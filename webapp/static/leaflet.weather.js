L.Control.weather = L.Control.extend({

    options: {
        position: "bottomleft"
    },

    _dateFormat: "Y-m-d H:i",
    _layer: undefined,
    _popupLayer: undefined,
    _config: {},
    _scriptRoot: "",

    _scale: {
        temp: d3.scale.quantize()
            .domain([-5, 10])
            .range(colorbrewer.RdBu[11].reverse()),
        rain: d3.scale.quantize()
            .domain([0, 20])
            .range(colorbrewer.BuPu[9])
    },
    _legend: undefined,

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
            onEachFeature: L.Util.bind(this._onEachFeature, this),
            //middleware: L.Util.bind(this._middleware, this)
        });

        this._legend = new L.Control.weather.legend();
        this._legend.addTo(map);

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


        var type = this._config.values;
        this._legend.update(this._scale[type], type);
    },

    _toggleForecastInput: function() {
        var disabled = !this._config.forecast;
        $(".weather-forecast-hours", this._container).prop('disabled', disabled);
    },

    _defaultStyle: function(feature) {
        return {
            fillColor: this._color(feature),
            fillOpacity: 0.8,
            stroke: true,
            color: "#ccc",
            opacity: 1,
            weight: 1
        }
    },

    _highlightStyle: function(feature) {
        return {
            stroke: true,
            color: "#ccc",
            opacity: 1,
            weight: 4
        }
    },

    _color: function(feature) {
        var value;
        if (this._config.values == "temp" && this._config.forecast) {
            value = feature.properties["tmp_mean"];
        } else if (this._config.values == "temp" && !this._config.forecast) {
            value = feature.properties["temperature"];
        } else if (this._config.values == "rain" && this._config.forecast) {
            value = feature.properties["pwat_mean"];
        } else if (this._config.values == "rain" && !this._config.forecast) {
            value = feature.properties["rainfall"];
        }

        var scale = this._scale[this._config.values];

        return scale(value);
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
                    + "/" + this._config.raster + ".json"
                    + "?datetime=" + this._dateToString(this._config.date)
                    + "&hours=" + this._config.forecast_hours;
        } else {
            url =  "/observation"
                    + "/" + this._config.raster + ".json"
                    + "?datetime=" + this._dateToString(this._config.date);
        }

        return this._scriptRoot + url;
    },

    /*
    _middleware: function(data) {

        var min, max;

        if (this._config.values == "temp") {
            min = max = data[0].properties.temperature;

            for(var feature in data) {
                min = Math.min(min, feature.properties.temperature);
                max = Math.max(min, feature.properties.temperature);
            }

            // TODO: adapt scales?

        } else if (this._config.values == "rain") {
            min = max = data[0].properties.rainfall;

            for(var feature in data) {
                min = Math.min(min, feature.properties.rainfall);
                max = Math.max(min, feature.properties.rainfall);
            }

            // TODO: adapt scales?
        }

        return data;
    },
    */


    // Add events to show additional information, loadaded by ajax, for each
    // feature/cell
    _onEachFeature: function(feature, layer) {
        var popup = L.popup({
            className: "popup-loading"
        }, layer);

        if (this._config.forecast) {
          return;
        }


        layer.bindPopup(popup);

        layer.on({
            remove: function(e) {
                // TODO: remove listener
            },

            popupopen: L.Util.bind(this._onPopupOpen, this),

            popupclose: function(e) {
                var layer = e.target;
                layer.setStyle(this._defaultStyle(layer.feature));
                this._popupLayer.clearLayers();

                e.popup._ajaxRequest.abort();
            }
        }, this);
    },

    _onPopupOpen: function(e) {
        var layer = e.target;
        layer.setStyle(this._highlightStyle(layer.feature));

        // Closures ftw
        var popup = e.popup;
        var self = this;

        // Should come from a click...
        var latlng = popup.getLatLng();

        // Build request URL
        var url = this._scriptRoot + "/info/" + this._config.raster + ".json";
        var data = {
            forecast: this._config.forecast ? "True" : "False",
            datetime: this._dateToString(this._config.date),
            hours: this._config.forecast_hours,
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

        // Position Pop-Up
        var pos = latlng;
        var bounds = layer.getBounds();
        pos.lng = bounds.getCenter().lng;
        pos.lat = bounds.getNorth();
        popup.setLatLng(pos);
    },

    // Create HTML from the json response and display additional geometries.
    _onPopupLoad: function(popup, data) {
        $(popup._container).removeClass("popup-loading");

        var l = L.geoJson(data, {
			//style:,
			//onEachFeature:,
			pointToLayer: function (feature, latlng) {
				return L.circleMarker(latlng, {
					radius: 2,
					fillColor: "#ff7800",
                    fillOpacity: 0.8,
					color: "#000",
					weight: 1,
					opacity: 1,
				});
			}
		});

        this._popupLayer.addLayer(l);
        var content = this._renderInfo(data);
        popup.setContent(content);
    },

    _renderInfo: function(data) {
        var content = L.DomUtil.create("div");
        var h3 = L.DomUtil.create("h3", "name", content);
        h3.innerHTML = data.properties.name;

        var dl, dt, dd;
        dl = L.DomUtil.create("dl", "", content);
        for (var key in data.properties) {
            dt = L.DomUtil.create("dt", "", dl);
            dt.innerHTML = key;
            dd = L.DomUtil.create("dd", "", dl);
            dd.innerHTML = data.properties[key] + this._unit(key);
        }

        return content;
    },

    _unit: function(name) {
        if (name.indexOf("temperature") > -1 || name.indexOf("tmp") > -1) {
            return " &deg;C";
        }

        if (name.indexOf("rainfall") > -1 || name.indexOf("pwat") > -1) {
            return " kg/(m^2)";
        }

        if (name.indexOf("altitude") > -1) {
            return " m";
        }

        return "";
    },

    _createContainer: function() {
		var container, cell;
        container = L.DomUtil.create("div", "leaflet-control-weather");

        var select_raster = this._createSelect("weather-raster-type",
            {"station": "Station", "state": "State", "district": "District"});
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
        input_hours.min = 3;
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
            value: "2015-01-11 00:00",
            minDate: "2014/11/11",
            maxDate: "2015/01/11",
            format: this._dateFormat,

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

L.Control.weather.legend = L.Control.extend({

    options: {
        position: "bottomright",
        id: "leaflet-control-weather-legend"
    },

    initialize: function (options) {
        L.setOptions(this, options);
    },

    // Create all the HTML elements, events and layers
    onAdd: function (map) {
		var container;
        container = L.DomUtil.create("div", this.options.id);
        container.setAttribute("id", this.options.id);

        this._container = container;
        return container;
    },

    update: function (scale, title) {
        $(this._container).empty();
        colorlegend("#" + this.options.id, scale, "quantile", {title: title});
    },

    // Remove the container, events and layers
    onRemove: function (map) {
    }
});

L.control.weather = function (options) {
	return new L.Control.weather(options);
};
