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

	/* ---------- scroll reveal ---------- */
	var reveals = document.querySelectorAll(".reveal");
	var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

	if (reduce || !("IntersectionObserver" in window)) {
		reveals.forEach(function (el) {
			el.classList.add("is-in");
		});
	} else {
		document.documentElement.classList.add("reveal-init");

		var observer = new IntersectionObserver(
			function (entries) {
				entries.forEach(function (entry) {
					if (entry.isIntersecting) {
						entry.target.classList.add("is-in");
						observer.unobserve(entry.target);
					}
				});
			},
			{ rootMargin: "0px 0px -10% 0px", threshold: 0.1 }
		);

		reveals.forEach(function (el) {
			observer.observe(el);
		});
	}

	/* ---------- current year ---------- */
	var year = document.getElementById("year");
	if (year) {
		year.textContent = String(new Date().getFullYear());
	}
})();
