/* State → LGA picker.
 * Enhances any <select data-lga-picker> whose options are grouped by state (<optgroup>):
 * adds a State dropdown and shows only that state's LGAs. Without JS the grouped list still works.
 */
(function () {
  document.querySelectorAll("select[data-lga-picker]").forEach(lgaSel => {
    const groups = [...lgaSel.querySelectorAll("optgroup")].map(g => ({
      label: g.label,
      options: [...g.querySelectorAll("option")].map(o => ({value: o.value, text: o.textContent})),
    }));
    if (!groups.length) return;

    const option = (value, text) => {
      const o = document.createElement("option");
      o.value = value;
      o.textContent = text;
      return o;
    };

    const stateSel = document.createElement("select");
    stateSel.className = lgaSel.className;
    stateSel.id = lgaSel.id ? lgaSel.id + "_state" : "";
    stateSel.setAttribute("aria-label", "State");
    stateSel.appendChild(option("", "Select your state"));
    groups.forEach((g, i) => stateSel.appendChild(option(String(i), g.label)));

    function render(i) {
      lgaSel.innerHTML = "";
      lgaSel.appendChild(option("", i < 0 ? "Select your state first" : `Select your LGA (${groups[i].options.length})`));
      if (i >= 0) groups[i].options.forEach(o => lgaSel.appendChild(option(o.value, o.text)));
      lgaSel.disabled = i < 0;
    }

    const current = lgaSel.value;
    const idx = groups.findIndex(g => g.options.some(o => o.value === current && current !== ""));
    render(idx);
    if (idx >= 0) {
      stateSel.value = String(idx);
      lgaSel.value = current;
    }
    stateSel.addEventListener("change", () => render(stateSel.value === "" ? -1 : Number(stateSel.value)));

    // Place the State field just above the LGA field (inside its own labelled block when possible).
    const block = lgaSel.closest(".mb-3");
    if (block) {
      const wrap = document.createElement("div");
      wrap.className = "mb-3";
      const label = document.createElement("label");
      label.className = "form-label fw-semibold";
      label.htmlFor = stateSel.id;
      label.textContent = "State";
      wrap.append(label, stateSel);
      block.before(wrap);
    } else {
      stateSel.classList.add("me-2");
      lgaSel.before(stateSel);
    }
  });
})();
