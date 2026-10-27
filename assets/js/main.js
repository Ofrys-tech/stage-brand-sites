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
			var link = event.target.closest("a");
			if (!link || !nav.classList.contains("is-open")) {
				return;
			}

			var href = link.getAttribute("href") || "";
			setMenu(false, false);

			/* Close the sheet first, then scroll with the shared header offset.
			   Letting the browser follow the hash while the page is still locked
			   makes long pages land short of the section. */
			if (href.charAt(0) === "#" && href.length > 1) {
				var target = document.querySelector(href);
				if (target) {
					event.preventDefault();
					var behavior = window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
					window.setTimeout(function () {
						target.scrollIntoView({ behavior: behavior, block: "start" });
					}, 50);
				}
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

	/* ---------- back to top on the hub ---------- */
	var toTop = document.querySelector(".to-top");
	var requisites = document.querySelector(".contact_wide");

	if (toTop && requisites && "IntersectionObserver" in window) {
		var topObserver = new IntersectionObserver(function (entries) {
			entries.forEach(function (entry) {
				toTop.classList.toggle("is-visible", entry.isIntersecting);
			});
		}, { threshold: 0.2 });

		topObserver.observe(requisites);

		toTop.addEventListener("click", function () {
			window.scrollTo({
				top: 0,
				behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth"
			});
		});
	}

	/* ---------- current year ---------- */
	var year = document.getElementById("year");
	if (year) {
		year.textContent = String(new Date().getFullYear());
	}
})();
