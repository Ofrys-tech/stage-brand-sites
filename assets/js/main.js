/* Люди Бренды — hub page interactions */
(function () {
	"use strict";

	/* ---------- mobile menu ---------- */
	var burger = document.querySelector(".burger");
	var nav = document.getElementById("nav");

	if (burger && nav) {
		var wide = window.matchMedia("(min-width: 961px)");

		function setMenu(open, moveFocus) {
			burger.setAttribute("aria-expanded", String(open));
			nav.classList.toggle("is-open", open);
			document.documentElement.classList.toggle("menu-open", open);

			if (open && moveFocus) {
				var first = nav.querySelector("a");
				if (first) {
					first.focus();
				}
			}
		}

		burger.addEventListener("click", function (event) {
			var open = burger.getAttribute("aria-expanded") === "true";
			setMenu(!open, !open && event.detail === 0);
		});

		nav.addEventListener("click", function (event) {
			if (event.target.closest("a") && nav.classList.contains("is-open")) {
				setMenu(false, false);
			}
		});

		document.addEventListener("keydown", function (event) {
			if (event.key === "Escape" && nav.classList.contains("is-open")) {
				setMenu(false, false);
				burger.focus();
			}
		});

		/* If the viewport grows past the mobile breakpoint while the menu is
		   open, the fixed overlay disappears; drop the locked state with it. */
		if (wide.addEventListener) {
			wide.addEventListener("change", function (event) {
				if (event.matches) {
					setMenu(false, false);
				}
			});
		}
	}

	/* ---------- current year ---------- */
	var year = document.getElementById("year");
	if (year) {
		year.textContent = String(new Date().getFullYear());
	}
})();
