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

	/* ---------- smooth page transition from spectacle cards ---------- */
	var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
	var pageOverlay = null;
	var leaving = false;

	function playPageTransition(href) {
		if (reduceMotion.matches) {
			window.location.href = href;
			return;
		}

		if (!pageOverlay) {
			pageOverlay = document.createElement("div");
			pageOverlay.className = "page-transition";
			pageOverlay.setAttribute("aria-hidden", "true");
			document.body.appendChild(pageOverlay);
		}

		/* Paint the transparent start state before switching it to opaque. */
		void pageOverlay.offsetWidth;
		pageOverlay.classList.add("is-active");

		window.setTimeout(function () {
			window.location.href = href;
		}, 240);
	}

	document.addEventListener("click", function (event) {
		if (leaving || event.defaultPrevented || event.button !== 0) {
			return;
		}

		if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
			return;
		}

		var link = event.target.closest("a[data-page-transition]");
		if (!link || (link.target && link.target !== "_self") || link.hasAttribute("download")) {
			return;
		}

		var href = link.getAttribute("href");
		if (!href || href.charAt(0) === "#") {
			return;
		}

		leaving = true;
		event.preventDefault();
		playPageTransition(href);
	});

	window.addEventListener("pageshow", function (event) {
		if (event.persisted && pageOverlay) {
			pageOverlay.classList.remove("is-active");
			leaving = false;
		}
	});

	/* ---------- current year ---------- */
	var year = document.getElementById("year");
	if (year) {
		year.textContent = String(new Date().getFullYear());
	}
})();
