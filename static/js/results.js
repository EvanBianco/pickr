$(function() {

    // From results.html
    // =================
    // var interpretationCount = {{ count }}; 
    // var pickUsers = [];   // A list
    // var ownerUser = "{{ owner_user }}";
    // var userID = "{{ user_id }}";

    var current = 0;  // An index for stepping over the list
    var currentUser = pickUsers[current];

    pickDrawing.setup('image-div');
    var overlay = pickDrawing.addOverlay('data:image/png;base64,' + 
           overlay64);

    var updateInterpNo = function(n){
      $('#interp-no').text(parseInt(n+1));
    };

    var updateVoteCount = function(voteCount){
        // Set the element text to the vote count
        if ($('#me-button').hasClass('active')){
          // Only need to do this once
          $('#my-vote-count').text(parseInt(voteCount["votes"]));
          $('#vote-count').text('–');
        } else if ($('#everyone-button').hasClass('active')){
          $('#vote-count').text(parseInt(voteCount["votes"]));
          // Update the button to reflect users current choice
          var user_choice = voteCount["user_choice"];
          if (user_choice == 1){
              document.getElementById("thumbs-up").style.color = "green";
              document.getElementById("thumbs-down").style.color = "grey";
          } else if (user_choice ==-1){
              document.getElementById("thumbs-up").style.color = "grey";
              document.getElementById("thumbs-down").style.color = "red";
          } else {
              document.getElementById("thumbs-up").style.color = "grey";
              document.getElementById("thumbs-down").style.color = "grey";
          } // end of inner if
        } else {
          // User voted on the owner's interpretation
          $('#owner-vote-count').text(parseInt(voteCount["votes"]));
          $('#vote-count').text('–');
          // Update the button to reflect users current choice
          var user_choice = voteCount["user_choice"];
          document.getElementById("thumbs-up").style.color = "grey";
          document.getElementById("thumbs-down").style.color = "grey";
          if (user_choice == 1){
              document.getElementById("owner-thumbs-up").style.color = "green";
              document.getElementById("owner-thumbs-down").style.color = "grey";
          } else if (user_choice ==-1){
              document.getElementById("owner-thumbs-up").style.color = "grey";
              document.getElementById("owner-thumbs-down").style.color = "red";
          } else {
              document.getElementById("owner-thumbs-up").style.color = "grey";
              document.getElementById("owner-thumbs-down").style.color = "grey";
          } // end of inner if
        }
    };
   
    var loadPicks = function(user){
      $.get('/vote',
            {user:user, image_key:image_key}, 
            updateVoteCount
            );

      // This loads the picks for 'currentUser' who is not the 
      // currently-logged-in user, but the one in the pick
      // review cycle - the interpreter of the current pick.
      pickDrawing.load({user:user,
                        image_key: image_key
                        });
    };

    $('#me-button').on('click', function(){
        // Toggles the user's own interpretation
        $(this).button('toggle');
        if ($(this).hasClass('active')){
          loadPicks(userID);
          $('#owner-up-vote-button').addClass('disabled');
          $('#owner-down-vote-button').addClass('disabled');
          $('#up-vote-button').addClass('disabled');
          $('#down-vote-button').addClass('disabled');
          $('#next-button').addClass('disabled');
          $('#previous-button').addClass('disabled');
        } else {
          pickDrawing.clear(); // Bah, deletes everything!
        }
        if ($('#owner-button').hasClass('active')){
          $('#owner-button').button('toggle');
        }
        if ($('#everyone-button').hasClass('active')){
          $('#everyone-button').button('toggle');
        }
    });

    $('#owner-button').on('click', function(){
        $(this).button('toggle');
        if ($(this).hasClass('active')){
          $('#owner-up-vote-button').removeClass('disabled');
          $('#owner-down-vote-button').removeClass('disabled');
          $('#up-vote-button').addClass('disabled');
          $('#down-vote-button').addClass('disabled');
          $('#next-button').addClass('disabled');
          $('#previous-button').addClass('disabled');
          loadPicks(ownerUser);
        } else {
          pickDrawing.clear(); // Bah, deletes everything!
          $('#owner-up-vote-button').addClass('disabled');
          $('#owner-down-vote-button').addClass('disabled');
        }
        if ($('#me-button').hasClass('active')){
          $('#me-button').button('toggle');
        }
        if ($('#everyone-button').hasClass('active')){
          $('#everyone-button').button('toggle');
        }
    });

    $('#everyone-button').on('click', function(){
        // Toggles everyone else's interpretations
        // Then you can step over these with the 
        // previous-button and next-button

	if(userCount > 0){
        $(this).button('toggle');
        if ($(this).hasClass('active')){
          loadPicks(currentUser);
          $('#owner-up-vote-button').addClass('disabled');
          $('#owner-down-vote-button').addClass('disabled');
          $('#up-vote-button').removeClass('disabled');
          $('#down-vote-button').removeClass('disabled');

	    if(userCount > 1){
		$('#next-button').removeClass('disabled');
            } // Leave previous-button alone
        } else {
          pickDrawing.clear(); // Bah, deletes everything!
          $('#up-vote-button').addClass('disabled');
          $('#down-vote-button').addClass('disabled');
        }
        if ($('#owner-button').hasClass('active')){
          $('#owner-button').button('toggle');
        }
        if ($('#me-button').hasClass('active')){
          $('#me-button').button('toggle');
        }
	}
    });

    $('#previous-button').on('click', function(){


            $('#next-button').removeClass('disabled');
            --current;
            if (current === 0){
		$('#previous-button').addClass('disabled');
            }
            currentUser = pickUsers[current];
            loadPicks(currentUser);
            updateInterpNo(current);
	
    });

    $('#next-button').on('click', function(){
        $('#previous-button').removeClass('disabled');

        ++current;
        if (current == (userCount -1)){
          $('#next-button').addClass('disabled');
        }
        currentUser = pickUsers[current];
        loadPicks(currentUser);
        updateInterpNo(current);
    });
    
    var castVote = function(v, u){
       $.post('/vote',{
           user: u,
           image_key: image_key,
           vote: v
       }, updateVoteCount);
    };
    
    $('#up-vote-button').on('click', function(){
        castVote(1, currentUser);
    });

    $('#down-vote-button').on('click', function(){
        castVote(-1, currentUser);
    });
    
    $('#owner-up-vote-button').on('click', function(){
        castVote(1, ownerUser);
    });

    $('#owner-down-vote-button').on('click', function(){
        castVote(-1, ownerUser);
    });
    
    $( "#overlay-slider" )
        .slider({min: 0, max: 100, value:67, change: function( event, ui ) {
            console.log(overlay);
            overlay.animate({opacity: ui.value / 100});
        }});

  loadPicks(userID);

});
