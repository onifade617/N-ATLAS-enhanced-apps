"""LoRA / QLoRA fine-tuning of N-ATLaS on chat-format JSONL from ``natlas_health.dataset``.

    pip install "natlas-health[finetune]"
    huggingface-cli login                       # accept the NCAIR1/N-ATLaS terms first
    python finetune/train_lora.py --train finetune/data/train.jsonl --eval finetune/data/eval.jsonl \
        --output runs/lafiya-lora --4bit

Needs one NVIDIA GPU: ~24 GB for LoRA, ~12 GB with --4bit (QLoRA); bf16 where supported, else fp16.
The output directory holds a LoRA adapter (tens of MB), not a full model; serve it next to the base model, e.g.

    vllm serve NCAIR1/N-ATLaS --enable-lora --lora-modules lafiya=runs/lafiya-lora --max-model-len 8192
    python -m natlas_health eval --base-url http://localhost:8000 --report after.md   # NATLAS_MODEL=lafiya

and compare with the base model's report before shipping. Only the final assistant answer is trained on.
Written for TRL >= 0.20 (SFTConfig.max_length, conversational prompt/completion data). Not yet run on a GPU.
"""

import argparse
import json


def load_examples(path):
    """Messages -> conversational prompt/completion pairs, so only the final answer is trained on."""
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                messages = json.loads(line)["messages"]
                rows.append({"prompt": messages[:-1], "completion": messages[-1:]})
    return rows


def main():
    p = argparse.ArgumentParser(description="LoRA fine-tuning for N-ATLaS")
    p.add_argument("--train", required=True)
    p.add_argument("--eval")
    p.add_argument("--base-model", default="NCAIR1/N-ATLaS")
    p.add_argument("--output", default="runs/natlas-lora")
    p.add_argument("--epochs", type=float, default=3)
    p.add_argument("--lr", type=float, default=2e-4)
    p.add_argument("--batch-size", type=int, default=4)
    p.add_argument("--grad-accum", type=int, default=4)
    p.add_argument("--max-length", type=int, default=2048)
    p.add_argument("--lora-r", type=int, default=16)
    p.add_argument("--lora-alpha", type=int, default=32)
    p.add_argument("--lora-dropout", type=float, default=0.05)
    p.add_argument("--4bit", dest="four_bit", action="store_true", help="QLoRA: load the base model in 4-bit")
    p.add_argument("--seed", type=int, default=13)
    args = p.parse_args()

    # Heavy imports here so --help works without the training stack installed.
    import torch
    from datasets import Dataset
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import SFTConfig, SFTTrainer

    tokenizer = AutoTokenizer.from_pretrained(args.base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # bf16 on Ampere and newer (A10, L4, A100); fp16 on older GPUs such as the T4 and V100 (e.g. free Colab).
    bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    dtype = torch.bfloat16 if bf16 else torch.float16

    quant = None
    if args.four_bit:
        quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                   bnb_4bit_compute_dtype=dtype, bnb_4bit_use_double_quant=True)
    model = AutoModelForCausalLM.from_pretrained(args.base_model, torch_dtype=dtype,
                                                 quantization_config=quant, device_map="auto")

    lora = LoraConfig(r=args.lora_r, lora_alpha=args.lora_alpha, lora_dropout=args.lora_dropout, bias="none",
                      task_type="CAUSAL_LM",
                      target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"])

    train = Dataset.from_list(load_examples(args.train))
    evaluation = Dataset.from_list(load_examples(args.eval)) if args.eval else None

    config = SFTConfig(
        output_dir=args.output,
        num_train_epochs=args.epochs,
        learning_rate=args.lr,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        lr_scheduler_type="cosine",
        warmup_ratio=0.05,
        bf16=bf16,
        fp16=not bf16,
        logging_steps=10,
        eval_strategy="epoch" if evaluation is not None else "no",
        save_strategy="epoch",
        save_total_limit=2,
        max_length=args.max_length,
        completion_only_loss=True,  # learn the answers, not the system prompt and facts
        gradient_checkpointing=True,
        report_to="none",
        seed=args.seed,
    )
    trainer = SFTTrainer(model=model, args=config, train_dataset=train, eval_dataset=evaluation,
                         processing_class=tokenizer, peft_config=lora)
    trainer.train()
    trainer.save_model(args.output)
    tokenizer.save_pretrained(args.output)
    print(f"LoRA adapter saved to {args.output}")


if __name__ == "__main__":
    main()
