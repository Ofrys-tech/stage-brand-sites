/* Люди Бренды — motion pass: header state, spotlight, drift, counters */
(function () {
	"use strict";

	var reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
	var header = document.querySelector(".site-header");
	var finePointer = window.matchMedia("(hover: hover) and (pointer: fine)");

	/* ---------- compact dark header after the first pixels ---------- */
	function updateHeader() {
		if (header) {
			header.classList.toggle("is-scrolled", window.scrollY > 12);
		}
	}

	/* ---------- scroll drift for decorative images ---------- */
	var driftItems = [];
	if (!reduce.matches) {
		Array.prototype.forEach.call(document.querySelectorAll("[data-drift]"), function (el) {
			driftItems.push({
				el: el,
				amount: parseFloat(el.getAttribute("data-drift")) || 0,
				rotate: parseFloat(el.getAttribute("data-drift-rotate")) || 0
			});
		});
	}

	function updateDrift() {
		var vh = window.innerHeight;

		driftItems.forEach(function (item) {
			var rect = item.el.getBoundingClientRect();
			if (rect.bottom < -240 || rect.top > vh + 240) {
				return;
			}

			var progress = (rect.top + rect.height / 2 - vh / 2) / vh;
			progress = Math.max(-1, Math.min(1, progress * 2));

			var shift = progress * item.amount;
			var rotation = progress * item.rotate;
			item.el.style.transform = "translate3d(0," + shift.toFixed(2) + "px,0)" +
				(rotation ? " rotate(" + rotation.toFixed(2) + "deg)" : "");
		});
	}

	var ticking = false;

	function onScroll() {
		if (ticking) {
			return;
		}

		ticking = true;
		window.requestAnimationFrame(function () {
			ticking = false;
			updateHeader();
			if (!reduce.matches) {
				updateDrift();
			}
		});
	}

	window.addEventListener("scroll", onScroll, { passive: true });
	window.addEventListener("resize", onScroll);
	onScroll();

	/* ---------- spotlight on the hub spectacle cards ---------- */
	if (finePointer.matches && !reduce.matches) {
		Array.prototype.forEach.call(document.querySelectorAll(".card"), function (card) {
			card.addEventListener("pointermove", function (event) {
				var rect = card.getBoundingClientRect();
				card.style.setProperty("--mx", ((event.clientX - rect.left) / rect.width * 100).toFixed(1) + "%");
				card.style.setProperty("--my", ((event.clientY - rect.top) / rect.height * 100).toFixed(1) + "%");
			});
		});
	}

	/* ---------- count the show facts when they enter the viewport ---------- */
	if (!reduce.matches && "IntersectionObserver" in window) {
		var counters = document.querySelectorAll("[data-count]");
		var counterObserver = new IntersectionObserver(function (entries) {
			entries.forEach(function (entry) {
				if (!entry.isIntersecting) {
					return;
				}

				counterObserver.unobserve(entry.target);
				countUp(entry.target);
			});
		}, { threshold: 0.6 });

		Array.prototype.forEach.call(counters, function (el) {
			counterObserver.observe(el);
		});
	}

	function countUp(el) {
		var target = parseInt(el.getAttribute("data-count"), 10);
		if (!isFinite(target)) {
			return;
		}

		var duration = 1100;
		var start = performance.now();
		el.textContent = "0";

		function frame(now) {
			var progress = Math.min(1, (now - start) / duration);
			var eased = 1 - Math.pow(1 - progress, 3);
			el.textContent = String(Math.round(target * eased));

			if (progress < 1) {
				window.requestAnimationFrame(frame);
			}
		}

		window.requestAnimationFrame(frame);
	}
})();
