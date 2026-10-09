"""Audio helpers. The gateway speaks WAV; WhatsApp and most mobile networks want compressed audio."""

import io
import wave


def wav_to_mp3(wav_bytes, bit_rate=32):
    """Return MP3 bytes, or None if the optional ``lameenc`` package is missing or the WAV is not 16-bit PCM.

    pip install "natlas-health[audio]"
    """
    try:
        import lameenc
    except ImportError:
        return None
    with wave.open(io.BytesIO(wav_bytes)) as w:
        if w.getsampwidth() != 2:
            return None
        rate, channels, pcm = w.getframerate(), w.getnchannels(), w.readframes(w.getnframes())
    enc = lameenc.Encoder()
    enc.set_bit_rate(bit_rate)
    enc.set_in_sample_rate(rate)
    enc.set_channels(channels)
    enc.set_quality(5)
    return bytes(enc.encode(pcm) + enc.flush())


def wav_duration(wav_bytes):
    with wave.open(io.BytesIO(wav_bytes)) as w:
        return w.getnframes() / float(w.getframerate())
