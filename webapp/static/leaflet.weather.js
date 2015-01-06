


L.Control.weather = L.Control.extend({

    options: {
        position: "topleft"
    },

    _dateFormat: "Y-m-d H:i",
    _layer: undefined,
    _popupLayer: undefined,
    _config: {},
    _scriptRoot: "",

    initialize: function (scriptRoot, options) {
        L.setOptions(this, options);
        // L.Control.prototype.initialize.call(this, options);

        this._scriptRoot = scriptRoot;

        // Store as a global for debugging
        window.weather = this;
    },

    // Create all the HTML elements, events and layers
    onAdd: function (map) {
        this._container = this._createContainer();

        L.DomEvent.disableClickPropagation(this._container);
        // TODO: Events with Leaflet?
        this._jquery_change_handler = L.Util.bind(this._update, this);
        $(this._container).on("change", this._jquery_change_handler);

        // Initialize the geojson layer
        this._layer = new L.GeoJSON.AJAX();
        L.setOptions(this._layer, {
            style: L.Util.bind(this._defaultStyle, this),
            onEachFeature: L.Util.bind(this._onEachFeature, this)
        });

        this._update();

        map.addLayer(this._layer);

        this._popupLayer = new L.LayerGroup();
        map.addLayer(this._popupLayer);

        return this._container;
    },

    // Remove the container, events and layers
    onRemove: function(map) {
        $(this._container).off("change", this._jquery_change_handler);
        map.removeLayer(this._layer);
        map.remove(this._popupLayer);
    },

    // Called whenever the config changes and the correct geometry has to be displayed
    _update: function() {
        var url;

        this._readConfig();
        this._toggleForecastInput();

        url = this.getURL();
        console.log(url);

        this._layer.refresh(url);
    },

    _toggleForecastInput: function() {
        var disabled = !this._config.forecast;
        $(".weather-forecast-hours", this._container).prop('disabled', disabled);
    },

    _defaultStyle: function(feature) {
        return {
            color: this._color(feature)
        }
    },

    _highlightStyle: function(feature) {
        return {
            color: "#000000"
        }
    },

    _color: function(feature) {
        var color;

        if (this._config.values == "temp") {

        } else if (this._config.values == "rain") {

        }

        color = ["#ff0000", "#00ff00", "#0000ff "][Math.floor(Math.random()*2.99)];

        return color;
    },

    // Read the current config from the html input fields and store it
    _readConfig: function() {
        // TODO: think about jquery and stuff
        var container = this._container;

        var dateobj = Date.parseDate($("#weather-date", container).val(),
                                  this._dateFormat);

        var date = {
            year:  dateobj.dateFormat("Y"),
            month: dateobj.dateFormat("m"),
            day:   dateobj.dateFormat("d"),
            hour:  dateobj.dateFormat("H")
        };

        var forecast_hours = $(".weather-forecast-hours", container).val();
        if (forecast_hours.length < 2) {
            forecast_hours = "0" + forecast_hours;
        }

        var forecast = $(".weather-forecast-flag", container).prop("checked");
        if (!forecast) {
            date.hour = "00";
        }

        this._config = {
            raster: $("#weather-raster-type", container).val(),
            values: $("#weather-values-type", container).val(),
            forecast: forecast,
            forecast_hours: forecast_hours,
            date: date
        };
    },

    _dateToString: function(date) {
        return date.year + date.month + date.day + date.hour;
    },

    // Get the URL for the current config
    getURL: function() {
        var url;

        if (this._config.forecast) {
            url =  "/forecast"
                    + "/" + this._config.raster
                    + "/" + this._dateToString(this._config.date)
                    + "/" + this._config.forecast_hours
                    + ".json";
        } else {
            url =  "/observation"
                    + "/" + this._config.raster
                    + "/" + this._dateToString(this._config.date)
                    + ".json";
        }

        return this._scriptRoot + url;
    },


    // Add events to show additional information, loadaded by ajax, for each
    // feature/cell
    _onEachFeature: function(feature, layer) {
        var popup = L.popup({
            className: "popup-loading"
        }, layer);

        layer.bindPopup(popup);

        layer.on({
            remove: function(e) {
                // TODO: remove listener
            },

            popupopen: function(e) {
                console.log(e);
                var layer = e.target;
                layer.setStyle(this._highlightStyle(layer.feature));

                // Closures ftw
                var popup = e.popup;
                var self = this;

                // Should come from a click...
                var latlng = popup.getLatLng();

                var url = this._scriptRoot + "/info/" + this._config.raster + ".json";
                var data = {
                    forecast: this._config.forecast ? "True" : "False",
                    datetime: this._dateToString(this._config.date),
                    lat: latlng.lat,
                    lon: latlng.lng
                };

                var request = $.getJSON(url, data, function(data, textStatus, jqXHR) {
                    self._onPopupLoad(popup, data, textStatus, jqXHR);
                });
                request.fail(function() {
                    $(popup._container).removeClass("popup-loading");
                    $(popup._container).addClass("popup-loading-error");
                });
                popup._ajaxRequest = request;
            },

            popupclose: function(e) {
                var layer = e.target;
                layer.setStyle(this._defaultStyle(layer.feature));
                this._popupLayer.clearLayers();

                e.popup._ajaxRequest.abort();
            }
        }, this);
    },

    // Create HTML from the json response and display additional geometries.
    _onPopupLoad: function(popup, data) {
        $(popup._container).removeClass("popup-loading");

        var l = L.geoJson(data, {
			//style:,
			//onEachFeature:,
			pointToLayer: function (feature, latlng) {
				return L.circleMarker(latlng, {
					radius: 8,
					fillColor: "#ff7800",
					color: "#000",
					weight: 1,
					opacity: 1,
					fillOpacity: 0.8
				});
			}
		});

        var pos = popup.getLatLng();
        var bounds = l.getBounds();

        if (data.geometry.type == "Point") {
            pos = bounds.getCenter();
        } else {
            pos.lng = bounds.getCenter().lng;
            pos.lat = bounds.getNorth();
        }

        this._popupLayer.addLayer(l);

        var content = "<h3>" + data.properties.name + "</h3>" +
                      "<dl>" +
                        "<dt>Temperature</dt><dd>" + data.properties.temperature + "&deg;C</dd>" +
                        "<dt>Mean Temperature</dt><dd>" + data.properties["mean temperature"] + "&deg;C </dd>" +
                      "</dl>";

        popup.setLatLng(pos);
        popup.setContent(content);
    },


    _createContainer: function() {
		var container, cell;
        container = L.DomUtil.create("div", "leaflet-control-weather");

        var select_raster = this._createSelect("weather-raster-type",
            {"district": "District", "state": "State", "station": "Station"});
        this._createColumn("Raster", select_raster, container);

        var select_values = this._createSelect("weather-values-type",
            {"temp": "Temperature", "rain": "Rainfall"});
        this._createColumn("Values", select_values, container);

        var input_date = this._createDatePicker("weather-date");
        this._createColumn("Date", input_date, container);


        // TODO: gfs/dwd text
        cell = L.DomUtil.create("div", "cell");

        var input_forecast_flag;
        input_forecast_flag = L.DomUtil.create("input", "weather-forecast-flag");
        input_forecast_flag.type = "checkbox";
        input_forecast_flag.defaultChecked = false;
        cell.appendChild(input_forecast_flag);

        var input_hours;
        input_hours = L.DomUtil.create("input", "weather-forecast-hours");
        input_hours.type = "range";
        input_hours.value = 0;
        input_hours.min = 0;
        input_hours.max = 129;
        input_hours.step = 3;
        cell.appendChild(input_hours);

        // TODO: display +hours somewhere

        this._createColumn("Forecast", cell, container);

        return container


    },

    // Create a select element with the given name and the key: value pairs as options
    _createSelect: function(name, options) {
        var select, key, name, option;

        select = document.createElement("select");
        select.setAttribute("id", name);
        select.setAttribute("name", name);
        select.setAttribute("class", name);

        for (key in options) {
            name = options[key];

            option = document.createElement("option");
            option.setAttribute("value", key);
            option.innerHTML = name;

            select.appendChild(option);
        }

        return select;
    },

    // Create an input element, which is handled by a jquery datetimepicker
    // TODO: replace by html5 <input type=date> and an additional hour field
    _createDatePicker: function(name) {
        var input;

        input = document.createElement("input");
        input.setAttribute("id", name);
        input.setAttribute("name", name);
        input.setAttribute("class", name);

        var now, hour;
        now = new Date();
        hour = Math.floor(now.getHours() / 6) * 6;
        now.setHours(hour, 0);

        $(input).datetimepicker({
            //TODO: value: now.dateFormat(this._dateFormat),
            value: "2014-12-01 00:00",
            format: this._dateFormat,

            maxDate: 0,
            closeOnDateSelect: true,

            step: 60,
            allowTimes: ["00:00", "06:00", "12:00", "18:00"],
            formatTime: "H:i",
            // allowTimes: ["00", "06", "12", "18"],
            scrollTime: false
        });

        return input;
    },

    _createColumn: function(name, cell, container) {
        var column, label;
        column = L.DomUtil.create("div", "leaflet-control-weather-column");

        if (name instanceof Element) {
            label = L.DomUtil.create("div", "leaflet-control-weather-column-label");
            label.appendChild(name);
        } else {
            label = L.DomUtil.create("label", "leaflet-control-weather-column-label");
            label.innerHTML = name;
            // TODO: check for name and add "for" attribute
        }

        column.appendChild(label);
        column.appendChild(cell);

        if (container) {
			container.appendChild(column);
		}

        return column;
    }
});

L.control.weather = function (options) {
	return new L.Control.weather(options);
};