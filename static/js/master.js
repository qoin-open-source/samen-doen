$(window).resize(function() {
  $.modal.resize();
});

jQuery(document).ready(function($) {

  
  $( ".element.accordion" ).accordion({ heightStyle: "content" });

  $('.attach-images .disabled').focus(function(){
    $(this).removeClass('disabled');
  }).blur(function(){
    $(this).addClass('disabled');
  });

  $(":input[placeholder]").placeholder();

  $("input[type=file]").fileinput('<button class="fileinput"><span></span></button>');

  $('.tp').tooltip({ placement: 'bottom', delay: { show: 0, hide: 500 }});

  $( ".element.datepicker input" ).datepicker({
        showOn: "button",
        buttonImage: "/assets/images/icons/calendar.png",
        buttonImageOnly: true,
        beforeShow: function(input, inst)
            {
                inst.dpDiv.css({marginTop: '15px', marginLeft: (input.offsetWidth - 93) + 'px'});
            }
  });

  if (typeof(current_language) != 'undefined') {
    $( "#datepicker" ).datepicker( 
        "option",
        $.datepicker.regional[ current_language ] 
    );
  }

  $('.target_toggle').click(function(e){
      e.preventDefault();
      target = $(this).data('target');
      $(this).hide();
      $(target).show();
  });

  //https://github.com/kylefox/jquery-modal
  $.modal.defaults = {
    overlay: "#000",        // Overlay color
    opacity: 0.75,          // Overlay opacity
    zIndex: 999,              // Overlay z-index.
    escapeClose: true,      // Allows the user to close the modal by pressing `ESC`
    clickClose: true,       // Allows the user to close the modal by clicking the overlay
    closeText: 'Close',     // Text content for the close <a> tag.
    showClose: false,        // Shows a (X) icon/link in the top-right corner
    modalClass: "modal",    // CSS class added to the element being displayed in the modal.
    spinnerHtml: null,      // HTML appended to the default spinner during AJAX requests.
    showSpinner: true       // Enable/disable the default spinner during AJAX requests.
  };

  $('.typeahead input').typeahead({
    name: 'accounts',
    local: ['Lorem ipsum dolor', 'Lusce bibendum', 'Purus Fringilla Risus', 'Cras Venenatis Fusce', 'Vehicula Bibendum']
  });

  $(".element.filter-select select").selecter({
    customClass: "filter"
  });

  $(".element.select select").selecter({ customClass: "normal-select" });

  $('.element.keywords .keyword').keyup(function(){
    var val = $(this).val(),
        $info = $(this).parent().find('.info');

    if(val !== '')
    {
      $info.css('display', 'block');
    }
    else
    {
      $info.css('display', 'none');
    }
  });
/*
  $(".royalSlider").royalSlider({
      keyboardNavEnabled: true,
      autoScaleSlider: true,
      autoScaleSliderWidth: 1400,
      autoScaleSliderHeight: 250,
      imageScaleMode: 'none',
      navigateByClick: false,
      controlNavigation: 'none',
      arrowsNav: false,
      imageScalePadding: 0,
      loop: true,
      imageAlignCenter: false,
      autoPlay: {
        enabled: true,
        pauseOnHover: true,
        delay: 4000
      }
  });*/

  $('.filter-box .title').click(function(e){
    e.preventDefault();
    $(this).parent().find('.options').slideToggle().promise().done(function(){
      $(this).parent().toggleClass('active');
    });
  });

  // Show hide sub-categories.
  $('.filter-box .toggle-sub-categories').click(function(e){
    $other_subcategory_toggles = $('.element.filter-box .toggle-sub-categories').not(this);
    $other_subcategory_toggles.removeClass('active');
    $other_subcategory_toggles.parent().parent().find('ul').hide();
    $(this).toggleClass('active');
    $(this).parent().parent().find('ul').toggle();
  });

  // Show open sub-categories list if one is checked.
  $('.filter-box .categories .sub-filter input:checked').each(function() {
    $(this).closest('ul').parent().find('.toggle-sub-categories').addClass('active');
    $(this).closest('ul').show();
  });

  // default on page load - hide long title
  $('.item_title.long').hide();
  $('.item_title.short').show();

  $('.marketplace .view a').click(function(e){
    e.preventDefault();
    var cookieExpires = 365;
    var view_type = $(this).prop('class')
    $.cookie("cc3_cookie_view_type", view_type, {
      expires: cookieExpires,
      path: '/'
    });
    $('.marketplace').removeClass('grid list').addClass($(this).prop('class'));
    $(this).addClass('active').siblings().removeClass('active');
    if (view_type == 'grid') {
      $('.item_title.long').hide();
      $('.item_title.short').show();
    } else {
      $('.item_title.short').hide();
      $('.item_title.long').show();
    }
  });


  // Add last-child to certain elements
  $('.add_last').find('> :last-child').addClass('last-child');
  $('.add_first').find('> :first-child').addClass('first-child');

  // Content Tabs Zebra
  $(".tabContents .item:odd, .contentTabs .items li:odd, .middle-bar .menu li ul li:odd, .account-menu ul li:odd, .zebra tr:odd, .sbmenu > li:odd").addClass("odd");
  $(".contentTabs .items li:even, .middle-bar .menu li ul li:even, .account-menu ul li:even, .zebra tr:even, .sbmenu > li:even").addClass("even");

  /*$('.middle-bar .menu ul > li').click(function(e){
    e.preventDefault();
    $(this).parent().find('li').removeClass('active');
    $(this).toggleClass('active');
  });
*/

  $(".item_counter").each(function(){
      var count = 1,
          $li = $(this).find('li'),
          $div = $(this).find('> div');

      $li.each(function(){
          $(this).addClass("item_" + count);
          count = count + 1;
      });

      $div.each(function(){
          $(this).addClass("item_" + count);
          count = count + 1;
      });
  });

  // BAR TOGGLES
  $('.top-bar .buttons a').click(function(e){
//    e.preventDefault();
    var viewClass = $(this).parent().prop('class'),
        $target = $('.middle-bar').find('.' + viewClass);

    if ($target ) {
        if( ! $target.is(':visible'))
        {
          $(this).parents('.buttons').find('a').removeClass('active');
          $('.middle-bar').children().not(".sub-navigation").hide();
        }

        $(this).toggleClass('active');
        $('.middle-bar').find('.' + viewClass).toggle();
    }
  });


  $('.header.only300 .expand-top a').click(function(e){

    e.preventDefault();

    var viewClass = $(this).prop('class'),
        $middleBar = $(this).parents('.header').find('.top-overlay'),
        $target = $middleBar.find('.' + viewClass);

    if( ! $target.is(':visible'))
    {
      $(this).parent().find('a').removeClass('active');
      $middleBar.children().hide();
    }

    $(this).toggleClass('active');
    $middleBar.find('.' + viewClass).toggle();

  });

  $('.header.only300 .expand-middle a.expander').click(function(e){
    e.preventDefault();
    var viewClasses = $(this).prop('class').split(" ");
    var viewClass = viewClasses[0], //$(this).prop('class'),
        $middleBar = $(this).parents('.header').find('.middle-bar'),
        $target = $middleBar.find('.' + viewClass);

    if( ! $target.is(':visible'))
    {
      $(this).parents('.buttons').find('li').removeClass('active');
      $middleBar.children().hide();
    }

    $(this).parent().toggleClass('active');
    $middleBar.find('.' + viewClass).toggle();
  });

  $('.header.only300 .tagline .show').click(function(e){
    $(this).parent().hide();
    $(this).parents('.row').find('.tagline').show();
  });

  // SIDEBAR MENU MOBILE
  $('.sidebar-menu .active-item a').click(function(){
    $(this).parent().next().toggle();
  });

  // TABLE MY ADS MOBILE
  $('.mobile-table .more-details').hide();
  $('.mobile-table .overview').click(function(){
    $(this).next().slideToggle();
  });

  // LATEST OFFERS AND WANTS
  $(".tabContents").hide();
  $(".tabContents.show").show();
  $(".tabContainer a.show").addClass('active');


  $(".tabContainer a").click(function(event){
       event.preventDefault();
       var $target = $(this).data('target');

       $(".tabContainer a").removeClass("active");
       $(this).addClass("active");

       $(".tabContents").hide();
       $(".tabContents." + $target).show();
  });

  // CONTENT TABS * NEWS * FEEDS * BUZZ
  $(".contentTabs").each(function(){
    var $display = $(this).find('.tab-display'),
        $defaultContent = $(this).find('.tab.active .tab-content');

        $defaultContent.clone().appendTo($display);

        $(this).find('.tab').click(function(){
          $display.empty();
          $(this).addClass('active').siblings().removeClass('active');
          $(this).find('.tab-content').clone().appendTo($display);
        });
  });

  // functions for accordion style 'read more' links
  $(".readmore").each(function() {
      var self = $(this);
      self.wrap('<div class="readmore-wrapper"/></div>');
      $('<a>',{
              html: '<span class="l"></span><span class="c">' + gettext('Read more') + '</span><span class="r"></span>',
              class: 'readmore element button',
              href: '#',
              click: function(){
                  if ($(this).hasClass('readmore')) {
                      $(this).html('<span class="l"></span><span class="c">' + gettext('Read less') + ' </span><span class="r"></span>');
                      $(this).removeClass('readmore');
                      self.show();
                  } else {
                      $(this).html('<span class="l"></span><span class="c">' + gettext('Read more') + '</span><span class="r"></span>');
                      $(this).addClass('readmore element button');
                      self.hide();
                  }
                  return false;
              }
      }).prependTo('.readmore-wrapper');
  });
});
