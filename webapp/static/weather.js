$(document).ready(function() {

    // Create an OpenStreetMap layer
    var osmLayer= L.tileLayer('http://{s}.tile.osm.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors',
    });

    // Create a mapbox layer
    var mapboxLayer = L.tileLayer('http://api.tiles.mapbox.com/v4/kleingeist.kd8hkfea/{z}/{x}/{y}.png?access_token=pk.eyJ1Ijoia2xlaW5nZWlzdCIsImEiOiJINUdqcW1BIn0.BpqqE0r65J8JUlmWtHV2Ug', {
        attribution: 'Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, <a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, Imagery © <a href="http://mapbox.com">Mapbox</a>',
        maxZoom: 18
    });

    // Initialize the map centered at germany
    var map = L.map('map', {
        center: [51.179, 9.811],
        zoom: 6 ,
        layers: [mapboxLayer]
    });

    // Export the map to the global scope for debugging
    window.map = map;

    // Add a control to change between layers
    var baseLayers = {
        "OSM": osmLayer,
        "Mapbox": mapboxLayer
    };
    L.control.layers(baseLayers).addTo(map);

    // Add main weather control (and layer) to the map
    var weatherControl  = L.control.weather($SCRIPT_ROOT);
    weatherControl.addTo(map);
}); // End ready()
