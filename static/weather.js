$(document).ready(function() {

var map = L.map('map').setView([52.517, 13.383], 13);

// create an OpenStreetMap tile layer
var osmLayer = L.tileLayer('http://{s}.tile.osm.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors',
});

//add a control to switch the layers on and off
var baseLayers = {
    "OSM": osmLayer,
};

var overlays = {
//    "Hillshading": hillshadeLayer,
//    "GPX": gpxLayer,
};

var layers = L.control.layers(baseLayers, overlays).addTo(map)


// Try to get some shit
$.getJSON("/geo.json", function(data) {
    console.log("geo geladen");

    //polyLayer = L.polygon(data.coordinates)
    //console.log(polyLayer.toGeoJSON());

    var geoJsonLayer = L.geoJson(data)
    //geoJsonLayer.addTo(map);

    layers.addOverlay(geoJsonLayer, "geo");

});

// Click Handler Test
map.on("click", function(me) {
    console.log(me.latlng);

    // Try to get some point
    $.getJSON("/district.json",
        {lon:  me.latlng.lng, lat: me.latlng.lat},
        function(data) {
            console.log("geo geladen");

            var pt = L.geoJson(data)
            console.log(pt)
            pt.addTo(map)
    }).error(function() { console.log("json error")});


});

// End ready()
});