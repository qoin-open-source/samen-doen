$(function() {
  /*function log( message ) {
    $( "<div>" ).text( message ).prependTo( "#log" );
    $( "#log" ).scrollTop( 0 );
  }*/
 
  $( "#id_company" ).autocomplete({
    source: business_name_auto_url,
    minLength: 2,
    select: function( event, ui ) {
      // update email address
      var business_email_posting = $.post( email_for_business_url, { 'business_name':ui.item.value });

      business_email_posting.done(function( data ) {
        var $email_field = $( "#id_email" );
        $email_field.val(data);  
      });
      // deal with form errors
      business_email_posting.fail(function( data ) {
        alert('fail: ' + data);
      });
    }
  });
});