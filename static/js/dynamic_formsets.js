function del_aform(del) {
    var par_tr = del.parents('tr')
    par_tr.addClass('deleted');
    del.find(':checkbox').attr('checked', true);
}

function add_aform(inst, prefix, no_items_element) {
  // retrieve the total number of forms from the control form
  var total = parseInt($('#id_' + prefix + '-TOTAL_FORMS').val());

  // create the string for selecting the ul containing the formset
  var table = '#' + inst;

  // select the last element of the formset which is hidden
  var tr = $(table + ' tr:last-child');

    tr.find('input').removeAttr("readonly");

  // copy the element and append it to the formset
  var new_tr = tr.clone();

  // update the indices of the hidden empty form to be the last one
  // for the input element
  new_tr.find(':input').each(function () {
    var minusone = total - 1;
    var new_name = $(this).attr('name')
      .replace('-' + minusone.toString() + '-', '-' + total + '-');
      var new_id = $(this).attr('id')
      .replace('-' + minusone.toString() + '-', '-' + total + '-');
    $(this).attr('name', new_name);
      $(this).attr('id', new_id);

  });

  // set the on click event of the delete button to call the del_aform() function
  new_tr.find('.delete').click(del_aform);

  // append the newly created form to the formset
  new_tr.appendTo(table);

  // increment the total number of forms in the control form
  $('#id_' + prefix + '-TOTAL_FORMS').val(++total);

    //Hide the message that says there are no items to show
    $('#' + no_items_element).addClass('no_items');

    // set the event handler for the delete link
    $(".deletelink").on("click", function(e){
                del_aform($(this));
            });
}
