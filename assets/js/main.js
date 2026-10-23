/* Люди Бренды — hub page interactions */
(function () {
	"use strict";

	/* ---------- mobile menu ---------- */
	var burger = document.querySelector(".burger");
	var nav = document.getElementById("nav");

	if (burger && nav) {
		burger.addEventListener("click", function () {
			var open = burger.getAttribute("aria-expanded") === "true";
			burger.setAttribute("aria-expanded", String(!open));
			nav.classList.toggle("is-open", !open);
		});

		nav.addEventListener("click", function (event) {
			if (event.target.closest("a") && nav.classList.contains("is-open")) {
				nav.classList.remove("is-open");
				burger.setAttribute("aria-expanded", "false");
			}
		});

		document.addEventListener("keydown", function (event) {
			if (event.key === "Escape" && nav.classList.contains("is-open")) {
				nav.classList.remove("is-open");
				burger.setAttribute("aria-expanded", "false");
				burger.focus();
			}
		});
	}

	/* ---------- current year ---------- */
	var year = document.getElementById("year");
	if (year) {
		year.textContent = String(new Date().getFullYear());
	}
})();
