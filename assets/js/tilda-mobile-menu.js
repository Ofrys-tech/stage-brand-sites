/* Tilda pages: close the mobile menu on link activation, Escape and desktop resize.
   Tilda's own burger toggle only handles the burger; without this the menu stays
   open (and the page stays locked) when an in-page link is tapped. */
(function () {
	"use strict";

	/* The hero back pill sits inside a transformed Tilda artboard; on phones it
	   cannot float above the scaled hero. Put a body-level copy at the bottom
	   left and hide it while the menu sheet is open. */
	var backSource = document.querySelector(".lb-home");
	var backFloating = null;

	if (backSource && !document.querySelector(".lb-home-floating")) {
		backFloating = backSource.cloneNode(true);
		backFloating.classList.add("lb-home-floating");
		document.body.appendChild(backFloating);
	}

	function setFloatingVisible(visible) {
		if (backFloating) {
			backFloating.style.visibility = visible ? "" : "hidden";
		}
	}

	function closeMenu() {
		var shell = document.querySelector(".tmenu-mobile");
		var panel = document.querySelector(".tmenu-mobile__menucontent_hidden");
		var burger = document.querySelector(".t-menuburger");

		if (shell) {
			shell.classList.remove("tmenu-mobile_opened");
		}
		if (panel) {
			panel.style.display = "none";
		}
		if (burger) {
			burger.classList.remove("t-menuburger-opened");
			burger.setAttribute("aria-expanded", "false");
		}

		setFloatingVisible(true);
	}

	document.addEventListener("click", function (event) {
		if (event.target.closest(".tmenu-mobile__menucontent_hidden a")) {
			closeMenu();
		}
	});

	document.addEventListener("keydown", function (event) {
		if (event.key === "Escape") {
			closeMenu();
		}
	});

	var burgerButton = document.querySelector(".t-menuburger");
	if (burgerButton) {
		burgerButton.addEventListener("click", function () {
			window.setTimeout(function () {
				var shell = document.querySelector(".tmenu-mobile");
				setFloatingVisible(!(shell && shell.classList.contains("tmenu-mobile_opened")));
			}, 0);
		});
	}

	var wide = window.matchMedia("(min-width: 981px)");

	function onWide(event) {
		if (event.matches) {
			closeMenu();
		}
	}

	if (wide.addEventListener) {
		wide.addEventListener("change", onWide);
	} else if (wide.addListener) {
		wide.addListener(onWide);
	}
})();
