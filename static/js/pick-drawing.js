// Globals defined in pickpoint.html...
// image_url = "{{ img_obj.url(size=1200) }}";
// image_key = "{{ img_obj.id }}";
// baseImageWidth = "{{ img_obj.width }}";
// baseImageHeight = "{{ img_obj.height }}";
// pickstyle = "{{ img_obj.pickstyle }}";

pickDrawingSetup = function(){
    var pickrElement;
    var paper;
    var baseImage;
    
    window.ondragstart = function() { return false; } ;

    var owner_colour   = "#0000FF"; // Image owner
    var current_colour = "#00DD00"; // Current user
    var default_colour = "#FF0000"; // Everyone else

    var points = [];
    var circles = [];
    var linestrip;    
    
    var aspectRatio = baseImageWidth / baseImageHeight;
    var avgImageSize = (baseImageWidth + baseImageHeight) / 2;
    var penSize = avgImageSize / 200;
    var resizeScale = 1;
    
    var updatePaperSize = function(){
        var w = pickrElement.width();
        var h = w / aspectRatio;
        resizeScale = w / baseImageWidth;
        paper.setSize(w, h);
    };
    
    var setup = function(elementId)
    {
        pickrElement = $('#' + elementId);
        penSize = 1 + pickrElement.width() / 400;
        paper = Raphael(elementId);
  
        updatePaperSize();
        paper.setViewBox(0, 0, baseImageWidth, baseImageHeight);
        baseImage = paper.image(image_url, 0, 0, baseImageWidth, 
        baseImageHeight);
        $(window).resize(updatePaperSize);        
    };
    
    var addOverlay = function(url)
    {
        var overlay = paper.image(url, 0, 0, baseImageWidth, 
          baseImageHeight);
  overlay.undrag();
        return overlay.attr({opacity: 0.67});
    };

    var addCircle = function(x, y, colour)
    {
        var radius = 1 + penSize;
        var circle = paper.circle(x, y, radius);
        circle.attr({
            fill: colour,
            stroke: '#fff',
            opacity: 0.5
        });
        circles.push(circle);
    };
    
    var removeCircle = function(x, y)
    {
        var circle = _.find(circles, function(c){
            return c.attrs.cx === x && c.attrs.cy === y
            });
        circle.remove();
        var index = circles.indexOf(circle);
        circles.splice(index, 1);
    };
    
    var clearCircles = function()
    {
        circles.forEach(function(c){c.remove();});
        circles = [];   
    };
    
    var connectTheDots = function(colour){
        if (!!linestrip)
            linestrip.remove();
        if (points.length === 0)
            return;
        // points.sort(function(a,b){ 
        //     return parseInt(a.x) - parseInt(b.x); 
        //     });
        var path = '';
        path += 'M' + points[0].x + ',' + points[0].y; // moveTo
        points.forEach(function(p){
            path += 'L' + p.x + ',' + p.y; // lineTo
        });
        if (pickstyle === "polygons"){
          path += "Z"; // closed line
        }
        linestrip = paper.path(path);
        linestrip.attr({'stroke': colour});
        linestrip.attr({'stroke-width':penSize});
        linestrip.attr({'opacity':'0.5'});
    };
    
    var addPoint = function(point, colour){
        addCircle(point.x, point.y, colour);
        points.push(point);
        if (pickstyle === 'lines' || pickstyle === 'polygons'){
            connectTheDots(colour);
        }
    };
    
    var clickPoint = function(point){
        var data = { 
      image_key:image_key,
            x: Math.round(point.x / resizeScale),
            y: Math.round(point.y / resizeScale)
        };
        $.post('/update_pick', data, 
            function(){addPoint(data, default_colour )});
    };

    var removePoint = function(point){
        removeCircle(point.x, point.y);
        points = _.reject(points, function(p){
            return p.x === point.x && p.y === point.y;
        });
        if (pickstyle === 'lines' || pickstyle === 'polygons'){
            connectTheDots(default_colour);
        }
    };
    
    var clearPoints = function(){
        clearCircles();
        points = [];

        // Not sure why we connect after clearing...?
        if (pickstyle === 'lines' || pickstyle === 'polygons'){
            connectTheDots(default_colour);
        }
    };
    
    var loadPoints = function(parameters){
        // Functioon gets called from results.js
        // like so:
        //   pickDrawing.load({
        //       user:user,
        //       image_key:image_key
        //       });

        // This is the reason we can't have
        // multiplt users' picks at once, 
        // because clearPoints() has not
        // concept of who points 'belong' to.
        clearPoints();

        // Would it be better to send back the user
        // owner in the JSON payload?
        $.get('/update_pick?', parameters, function(data){
          if (data.current) {
            data.user_data.forEach(function(item){
              addPoint({x:item[0], y:item[1]},
              current_colour);
            });
          } else if (data.owner) {
            data.owner_data.forEach(function(item){
              addPoint({x:item[0], y:item[1]},
              owner_colour);
            });
          } else {
            data.data.forEach(function(item){
              addPoint({x:item[0], y:item[1]},
              default_colour);
            });
          }
        }, 'json');
    };
    
    return {
        setup: setup,
        addOverlay: addOverlay,
        clickPoint: clickPoint,
        removePoint: removePoint,
        clear: clearPoints,
        load: loadPoints
    }
};

var pickDrawing = pickDrawingSetup();
