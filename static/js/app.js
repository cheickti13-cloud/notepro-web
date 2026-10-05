// NotePro — petits comportements (aucun script inline : compatible CSP stricte)
document.addEventListener("DOMContentLoaded", function () {
  // Envoi automatique d'un formulaire au changement d'un <select data-autosubmit>
  document.querySelectorAll("select[data-autosubmit]").forEach(function (sel) {
    sel.addEventListener("change", function () { sel.form.submit(); });
  });
  // Confirmation avant une action irréversible : <button data-confirm="...">
  document.querySelectorAll("[data-confirm]").forEach(function (el) {
    el.addEventListener("click", function (e) {
      if (!window.confirm(el.getAttribute("data-confirm"))) { e.preventDefault(); }
    });
  });
  // Appel : affiche le champ « minutes de retard » seulement si « Retard » est choisi
  document.querySelectorAll("[data-statut-appel]").forEach(function (sel) {
    var cible = document.getElementById(sel.getAttribute("data-statut-appel"));
    function maj() { if (cible) { cible.hidden = sel.value !== "RETARD"; } }
    sel.addEventListener("change", maj); maj();
  });
});

// Menu latéral replié sur mobile : <button data-menu="id-de-l-entete">
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("[data-menu]").forEach(function (btn) {
    var cible = document.getElementById(btn.getAttribute("data-menu"));
    btn.addEventListener("click", function () {
      var ouvert = cible.classList.toggle("ouvert");
      btn.setAttribute("aria-expanded", ouvert ? "true" : "false");
    });
  });
});

// Navigation par liste déroulante : <select data-nav> dont les options sont des URL
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("select[data-nav]").forEach(function (sel) {
    sel.addEventListener("change", function () { if (sel.value) { window.location.href = sel.value; } });
  });
});
