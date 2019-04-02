$(function () {
	$('.navigation').tinyNav();
	$('.s-selecter').selecter();
	$('#modal').modal();

	$('input').iCheck({
		checkboxClass: 'icheckbox_square-grey',
		radioClass: 'iradio_square-grey'
	});

	$( ".datepicker input" ).datepicker({
	      showOn: "button",
	      buttonImage: "/assets/img/calendar-icon.png",
	      buttonImageOnly: true,
	      beforeShow: function(input, inst)
          {
              inst.dpDiv.css({marginTop: '15px', marginLeft: (input.offsetWidth - 93) + 'px'});
          }
	});
});
