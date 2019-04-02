var update_profile_in_progress = false;

$(function() {
    var csrftoken = $.cookie('csrftoken');
    
    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }
    $.ajaxSetup({
        crossDomain: false, // obviates need for sameOrigin test
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type)) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });


    /* attach a submit handler to the payment form */
    $("#update_profile_form").submit(function(event) {
        // if the confirmed input #id_confirmed has been added, submit form normally
        if (!update_profile_in_progress) {
            remove_errors();
            var $update_profile_form_errors = $( "#update_profile_form_errors" );
            
            // prevent double clicks / enter buttons
            update_profile_in_progress = true;
            $update_profile_form_errors.html('');
            $update_profile_form_errors.addClass ( 'hide' );
            $('#update_profile_form_button').hide();
            $('#update_profile_form_spinner').show();
            
            /* stop form from submitting normally */
            event.preventDefault();

            // make sure tinyMCE delivers to the textarea for POSTing
//            tinyMCE.triggerSave();

            /* Send the data via ajax - to avoid loosing file info if invalid*/
            $("#update_profile_form").ajaxSubmit(
                {
                    success:showSuccessPage,
                    error: show_errors,//function(data ) { alert(data); },
                }
            );
        }
        return false;
    });
})

function remove_errors() {

    try {
        item_input= $('#update_profile_form_errors');
        item_input.addClass('hide');
        var span_error_classes = $('span.error');
        span_error_classes.each(function(){
            this.remove();
        });
        var div_error_classes = $('div.error');
        div_error_classes.each(function(){
            this.removeClass('error');
        });

    }
    catch (e) {
        // not too worried with exceptions removing error spans/divs
    }
    
    $('.error').removeClass('error');
}

function show_errors(the_errors) {
    var errorObj = $.parseJSON( the_errors.responseText );
    for (var key in errorObj) {
        var item_input, to_append;
        if (key == '__all__'){
          item_input= $('#update_profile_form_errors');
          to_append = errorObj[key];
          item_input.append(to_append);
          item_input.addClass('element').addClass('form-error');
          item_input.removeClass('hide');
        } else {
          item_input= $('#id_' + key);       
          to_append = '<span class="error">' + errorObj[key] + '<br /></span><br />';
          item_input.parent().append(to_append);
          item_input.closest('.element.label').addClass('error'); //parent().parent()
        }
        
    }

    $('#update_profile_form_spinner').hide();
    $('#update_profile_form_button').show();
    update_profile_in_progress = false;
    return false;
}

function showSuccessPage() {
     window.location.replace(return_url);
}
