pickDrawingSetup = function(){
    var pickrElement;
    var paper;
    var baseImage;

    var points = [];
    var circles = [];
    var linestrip;    
    
    // TODO: Hard-coded base image size
    var aspectRatio = baseImageWidth / baseImageHeight;
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
        paper = Raphael(elementId);
        updatePaperSize();
        paper.setViewBox(0, 0, baseImageWidth, baseImageHeight);
        baseImage = paper.image(image_url, 0, 0, baseImageWidth, baseImageHeight);
        $(window).resize(updatePaperSize);        
    }
    
    var addOverlay = function(url)
    {
        var overlay = paper.image(url, 0, 0, baseImageWidth, baseImageHeight);
        return overlay.attr({opacity: 0.5});
    }

    var addCircle = function(x, y)
    {
        var radius = 4;
        var circle = paper.circle(x, y, radius);
        circle.attr({
            fill: '#f00',
            stroke: '#fff',
            opacity: 0.5
        });
        circles.push(circle);
    }
    
    var removeCircle = function(x, y)
    {
        var circle = _.find(circles, function(c){
            return c.attrs.cx === x && c.attrs.cy === y
            });
        circle.remove();
        var index = circles.indexOf(circle);
        circles.splice(index, 1);
    }
    
    var clearCircles = function()
    {
        circles.forEach(function(c){c.remove();});
        circles = [];   
    }
    
    var connectTheDots = function() // Lalalalala
    {
        if (!!linestrip)
            linestrip.remove();
        if (points.length === 0)
            return;
        points.sort(function(a,b){ 
            return parseInt(a.x) - parseInt(b.x); 
            });
        var path = '';
        path += 'M' + points[0].x + ',' + points[0].y; // moveTo
        points.forEach(function(p){
            path += 'L' + p.x + ',' + p.y; // lineTo
        });
        linestrip = paper.path(path);
        linestrip.attr({stroke: '#f00'});
    }
    
    var addPoint = function(point){
        addCircle(point.x, point.y);
        points.push(point);
        connectTheDots();
    }
    
    var clickPoint = function(point){
        var data = { 
	    image_key:image_key,
            x: Math.round(point.x / resizeScale),
            y: Math.round(point.y / resizeScale)
        };
        $.post('/update_pick', data, 
            function(){addPoint(data)});
    }

    var removePoint = function(point){
        removeCircle(point.x, point.y);
        points = _.reject(points, function(p){
            return p.x === point.x && p.y === point.y;
        });
        connectTheDots();
    }
    
    var clearPoints = function(point){
        clearCircles();
        points = [];
        connectTheDots();
    }
    
    var loadPoints = function(parameters)
    {
        clearPoints();
        $.get('/update_pick?', parameters, function(data)
        {
           data.forEach(function(item){
               addPoint({x:item[0], y:item[1]});
	       
           });
        }, 'json');
    }
    
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
