FORT_RADIUS = 1;
NEUTRAL_NAME = "neutral";
NEUTRAL_COLOR = "#7f7f7f";
PLAYER_COLORS = [
  "#1f77b4",
  "#ff7f0e",
  "#2ca02c",
  "#d62728",
  "#9467bd",
  "#8c564b",
  "#e377c2",
  "#bcbd22",
  "#17becf"
];

var takeSection = function (lines) {
  var header = lines.shift().split(/ +/);
  var length = parseInt(header[0]);
  var section = [];
  for (var i = 0; i < length; i++) {
    section.push(lines.shift());
  }
  return section;
};

var parseFort = function (string) {
  var words = string.split(/ +/);
  return {
    name:       words[0],
    x:          parseInt(words[1]),
    y:          parseInt(words[2]),
    owner:      words[3],
    garrison:   parseInt(words[4]),
    neighbours: []
  };
};

var parseRoad = function (string) {
  return string.split(/ +/);
};

var parseMarch = function (string) {
  var words = string.split(/ +/);
  return {
    origin: words[0],
    target: words[1],
    owner:  words[2],
    size:   parseInt(words[3]),
    steps:  parseInt(words[4])
  };
};

var parseData = function (lines, turn) {
  var forts = takeSection(lines).map(parseFort);
  var roads = takeSection(lines).map(parseRoad);
  var marches = takeSection(lines).map(parseMarch);

  var fortmap = {};
  forts.forEach(function (fort) {
    fortmap[fort.name] = fort;
  });

  roads.forEach(function (road) {
    road[0] = fortmap[road[0]];
    road[1] = fortmap[road[1]];
  });

  marches.forEach(function (m) {
    m.origin = fortmap[m.origin];
    m.target = fortmap[m.target];
    var dx = m.target.x - m.origin.x;
    var dy = m.target.y - m.origin.y;
    var alpha = Math.atan2(dy, dx);
    var x_step = Math.cos(alpha);
    var y_step = Math.sin(alpha);
    var dist = Math.ceil(dx / x_step);

    var dx_gates = dx - 2 * FORT_RADIUS * x_step;

    var k = (dx_gates/(dist-1)) / x_step;
    m.x = m.target.x - x_step * (FORT_RADIUS + k * (m.steps-0.5));
    m.y = m.target.y - y_step * (FORT_RADIUS + k * (m.steps-0.5));
    m.step_size = k;

    m.id = [m.origin.name, m.target.name, turn + m.steps - dist].join(' ');
  });

  return {
    forts:   d3.values(fortmap),
    roads:   roads,
    marches: marches
  };
};

var viewbox = function(xmin, ymin, xmax, ymax, edge){
  edge = edge || 0;
  return [xmin-edge, ymin-edge, xmax+2*edge, ymax+2*edge].map(function(n){
    return n.toString();
  }).join(' ');
};

var translate = function(x, y){
  return "translate("+x+","+y+")";
};

var visualize = function(game){
  $('#control-slider').on('change', function(e) {
    draw(game, parseInt(e.target.value));
  });
  $('#control-slider').attr('min', 0);
  $('#control-slider').attr('max', game.steps.length-1);
  draw(game, 0);
};

Game = function(steps) {
  this.steps = steps;
  this.playerColors = {};
  this.playerColors[NEUTRAL_NAME] = NEUTRAL_COLOR;
};

Game.prototype.getPlayerColor = function(name){
  var color = this.playerColors[name];
  if (color === undefined) {
    var num = Object.keys(this.playerColors).length - 1;
    this.playerColors[name] = PLAYER_COLORS[num];
    color = PLAYER_COLORS[num];
  }
  return color;
}

var drawLegend = function(game){
  var entryHeight = 20;
  var fig = d3.select("#legend");
  var newEntries = fig.selectAll(".legend-entry")
      .data(Object.keys(game.playerColors, function(d){return d}))
      .enter().append('g')
      .attr('class', 'legend-entry')
      .attr('transform', function(d, i){
        return translate(0, i * entryHeight);
      })

  newEntries.append('circle')
      .attr('cy', 8)
      .attr('cx', 8)
      .attr('r', 8)
      .attr('fill', function(d) {return game.getPlayerColor(d)});

  newEntries.append('text')
      .attr('x', 20)
      .attr('y', 12)
      .text(function(d) {return d});
}

var draw = function(game, step){
  var data = game.steps[step];
  var xmin = d3.min(data.forts, function(f) { return f.x });
  var ymin = d3.min(data.forts, function(f) { return f.y });
  var xmax = d3.max(data.forts, function(f) { return f.x });
  var ymax = d3.max(data.forts, function(f) { return f.y });

  var speed = parseInt($("#speed-slider").val());
  console.log(speed);

  var fig = d3.select("#visualisation")
      .attr("viewBox", viewbox(xmin, ymin, xmax, ymax, 2));

  fig.selectAll("line")
      .data(data.roads)
      .enter().append("line")
      .attr("stroke-width", 0.1)
      .attr("stroke", "gray")
      .attr("x1", function(d) {return d[0].x})
      .attr("y1", function(d) {return d[0].y})
      .attr("x2", function(d) {return d[1].x})
      .attr("y2", function(d) {return d[1].y});

  // MARCHES

  var marches = fig.selectAll(".march")
      .data(data.marches, function(d) {return d.id})

  var newMarches = marches.enter().append("g")
    .attr("class", "march")
    .attr("transform", function(d) {return translate(d.x, d.y)});

  newMarches.append("circle")
      .attr("r", function(d) {return d.step_size/2})
      .attr("fill", function(d) {return game.getPlayerColor(d.owner)});

  newMarches.append("text")
      .attr("font-size", function(d) {return .8*d.step_size})
      .attr("fill", "#fff")
      .attr("dy","0.3em")
      .attr("text-anchor", "middle")
      .text(function(d) {return d.size});

  marches.select("text")
      .transition()
      .duration(speed)
      .text(function(d) {return d.size});

  marches.data(data.marches, function(d) {return d.id})
      .transition()
      .duration(speed)
      .attr("transform", function(d) {return translate(d.x, d.y)})
      .style("opacity", 1);

  marches.exit()
      .transition()
      .duration(speed)
      .attr("transform", function(d) {
        if (d.steps == 1) {
          return translate(d.target.x, d.target.y)
        }
        return translate(d.x, d.y);
      })
      .style("opacity", 0)
      .remove();


  var newForts = fig.selectAll(".fort")
      .data(data.forts)
      .enter().append("g")
      .attr("class", "fort")
      .attr("transform", function(d) {return translate(d.x, d.y)});

  newForts.append("circle")
      .attr("r", FORT_RADIUS);
  newForts.append("text")
      .attr("font-size", .9 * FORT_RADIUS)
      .attr("fill", "#fff")
      .attr("dy","0.3em")
      .attr("text-anchor", "middle");

  var fortGroups = fig.selectAll(".fort");

  fortGroups.select("circle")
      .attr("fill", function(d) {return game.getPlayerColor(d.owner)});

  fortGroups.select("text")
      .text(function(d) {return d.garrison});

  drawLegend(game);
};


$.get('../arbiter/sample.data', function(dump){
  var raw = dump.split('\n'), lines = [];
  raw.forEach(function(val){
    if(! /^(#.*)?$/.test(val)){
      lines.push(val);
    }
  });
  var steps = [];
  while (lines.length > 0) {
    steps.push(parseData(lines, steps.length));
  }
  visualize(new Game(steps));
});
