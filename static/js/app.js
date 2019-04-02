$(function () {
	//$('.navigation').tinyNav();
	$('.s-selecter').selecter();
	$('#modal').modal();

	$.modal.defaults = {
		overlay: "#000",        // Overlay color
		opacity: 0.75,          // Overlay opacity
		zIndex: 555,              // Overlay z-index.
		escapeClose: true,      // Allows the user to close the modal by pressing `ESC`
		clickClose: true,       // Allows the user to close the modal by clicking the overlay
		closeText: 'Close',     // Text content for the close <a> tag.
		closeClass: '',         // Add additional class(es) to the close <a> tag.
		showClose: true,        // Shows a (X) icon/link in the top-right corner
		modalClass: "positoos-modal",    // CSS class added to the element being displayed in the modal.
		spinnerHtml: null,      // HTML appended to the default spinner during AJAX requests.
		showSpinner: true,      // Enable/disable the default spinner during AJAX requests.
		fadeDuration: null,     // Number of milliseconds the fade transition takes (null means no transition)
		fadeDelay: 1.0          // Point during the overlay's fade-in that the modal begins to fade in (.5 = 50%, 1.5 = 150%, etc.)
	};

	// Use this to trigger a modal
	// More info at http://github.com/kylefox/jquery-modal
	//$('#modal').modal();

	$('.saving-targets .btn').click(function() {
		$('#modal').modal();
	});
	$('input').iCheck({
		checkboxClass: 'icheckbox_square-grey',
		radioClass: 'iradio_square-grey',
	});

	$( ".datepicker input" ).datepicker({
	    showOn: "button",
	    buttonImage: "/assets/img/calendar-icon.png",
    	buttonImageOnly: true,
        beforeShow: function(input, inst)
        {
            inst.dpDiv.css({marginTop: '15px', marginLeft: (input.offsetWidth - 93) + 'px'});
        },
        changeYear: true,
        yearRange: "-100:+0"
	});

	$('.showcase-slide').each(function( index ) {
		var slideSRC = $(this).find('img.showcase-slide-bg').attr('src');
		$(this).find('img').hide();
		$(this).css('background-image', 'url(' + slideSRC + ')');
	});

    $('.billing-invoice-quick-menu').each(function(index, item) {
        var $menu_el = $(item);
        
        $menu_el.on('change', function(event) {
            var new_value = $menu_el.val();

            if (parseInt(new_value) !== -1) {
                window.location = $menu_el.val();
            }
        });
    });
});
