$(function() {
    var interpretationCount = count;
    var current = 0;
    pickDrawing.setup('image-div');
    //var overlay64 = 'iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==';
    var overlay = pickDrawing.addOverlay('data:image/png;base64,' + overlay64);
    
    var updateVoteCount = function(voteCount)
    {
        $('#vote-count').text(parseInt(voteCount["votes"]));
	// Update the button to reflect users current choice
	var user_choice = voteCount["user_choice"];

	if(user_choice == 1){
	    document.getElementById("thumbs-up").style.color = "green";
	    document.getElementById("thumbs-down").style.color = "grey";
	} else if(user_choice ==-1){
	    document.getElementById("thumbs-up").style.color = "grey";
	    document.getElementById("thumbs-down").style.color = "red";
	} else{
	    document.getElementById("thumbs-up").style.color = "grey";
	document.getElementById("thumbs-down").style.color = "grey";
    };


};


   
     var loadPicks = function()
    {


	    
	$.get('/vote', {index: current,
			image_key: image_key}, 
	      updateVoteCount);

	pickDrawing.load({
           pick_index: current,
	    image_key: image_key
        });
        
    };

    $('#previous-button').click(function(){
        if (current <= 0)
            return;
        --current;
        loadPicks();
    });

    $('#next-button').click(function(){
        if (current >= interpretationCount - 1)
            return;
        ++current;
        loadPicks();
    });
    
    var castVote = function(v)
    {
       $.post('/vote',{
           index: current,
	   image_key: image_key,
           vote: v
       },
       updateVoteCount);
    };
    
    $('#up-vote-button').click(function(){
        castVote(1);
    });

    $('#down-vote-button').click(function(){
        castVote(-1);
    });
    
    $( "#overlay-slider" )
        .slider({min: 0, max: 100, value:67, change: function( event, ui ) {
            console.log(overlay);
            overlay.animate({opacity: ui.value / 100});
        }});

loadPicks();
});



