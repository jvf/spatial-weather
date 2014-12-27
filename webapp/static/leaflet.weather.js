L.Control.weather = L.Control.extend({

    options: {
        position: "topleft"
    },

    _dateFormat: "Y-m-d H:i",
    _layer: undefined,
    _config: {},
    _scriptRoot: "",

    initialize: function (scriptRoot, options) {
        L.setOptions(this, options);
        // L.Control.prototype.initialize.call(this, options);

        this._scriptRoot = scriptRoot;

        // Store as a global for debugging
        window.weather = this;
    },

    // Create all the HTML elements, events and the AJAX geojson Layer
    onAdd: function (map) {
        this._container = this._createContainer();

        L.DomEvent.disableClickPropagation(this._container);
        // TODO: Events with Leaflet?
        $(this._container).on("change", null, this, this.onChange);

        // Initialize the geojson layer
        this._layer = new L.GeoJSON.AJAX();
        L.setOptions(this._layer, {
            style: this._getStyle()
        });
        this._update();

        map.addLayer(this._layer);

        return this._container;
    },

    onRemove: function(map) {
        $(this._container).off("change", null, this._onChange);
        map.removeLayer(this._layer);
    },

    // Fired by jQuery: calls _update in the context of the correct object
    onChange: function(event) {
        var that = event.data;
        that._update();
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

    // Return a closured style function, which has access to _this_.
    _getStyle: function() {
        var that = this;
        return (function(feature) {
            return {
                color: that._color(feature)
            }
        });
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

        this._config = {
            raster: $("#weather-raster-type", container).val(),
            values: $("#weather-values-type", container).val(),
            forecast: $(".weather-forecast-flag", container).prop("checked"),
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

        return container;
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
            value: now.dateFormat(this._dateFormat),
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