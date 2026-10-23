/* Люди Бренды — scroll reveals and image parallax */
(function () {
	"use strict";

	var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

	if (reduce || !("IntersectionObserver" in window)) {
		return;
	}

	var items = document.querySelectorAll(".reveal, .reveal_img");

	document.querySelectorAll("[data-reveal-group]").forEach(function (group) {
		Array.prototype.forEach.call(group.children, function (child, index) {
			child.style.setProperty("--i", String(index));
		});
	});

	var observer = new IntersectionObserver(
		function (entries) {
			entries.forEach(function (entry) {
				if (entry.isIntersecting) {
					entry.target.classList.add("is-in");
					observer.unobserve(entry.target);
				}
			});
		},
		{ threshold: 0.12, rootMargin: "0px 0px -8% 0px" }
	);

	items.forEach(function (el) {
		observer.observe(el);
	});

	/* Only now may the CSS hide unrevealed elements. If this script never runs,
	   or reduced motion is on, everything stays visible. */
	document.documentElement.classList.add("js-reveal");

	/* ---------- subtle parallax for large photos ---------- */
	var figures = Array.prototype.slice.call(document.querySelectorAll("[data-parallax]"));
	var wide = window.matchMedia("(min-width: 961px)");
	var ticking = false;

	function updateParallax() {
		ticking = false;
		if (!wide.matches || !figures.length) {
			return;
		}

		var vh = window.innerHeight;

		figures.forEach(function (figure) {
			var img = figure.querySelector("img");
			if (!img) {
				return;
			}

			var rect = figure.getBoundingClientRect();
			if (rect.bottom < -240 || rect.top > vh + 240) {
				return;
			}

			var offset = ((rect.top + rect.height / 2 - vh / 2) / vh) * -40;
			offset = Math.max(-24, Math.min(24, offset));
			img.style.transform = "translate3d(0," + offset.toFixed(2) + "px,0) scale(1.08)";
		});
	}

	function onScroll() {
		if (!ticking) {
			ticking = true;
			window.requestAnimationFrame(updateParallax);
		}
	}

	window.addEventListener("scroll", onScroll, { passive: true });
	window.addEventListener("resize", onScroll);
	updateParallax();
})();
