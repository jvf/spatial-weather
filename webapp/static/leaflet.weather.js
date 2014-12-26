L.Control.weather = L.Control.extend({

    options: {
        position: "topleft"
    },

    _dateFormat: 'Y/m/d H:i',
    _layer: undefined,

    initialize: function (options) {
        L.setOptions(this, options);
        // L.Control.prototype.initialize.call(this, options);

        // Store as a global for debugging
        window.weather = this;
    },

    // Create all the HTML elements, events and the AJAX geojson Layer
    onAdd: function (map) {
		this._container = L.DomUtil.create('div', 'leaflet-control-weather');
		L.DomEvent.disableClickPropagation(this._container);


        var select_raster, select_values;
        select_raster = this._createSelect('weather-raster-type',
            {'district': 'District', 'state': 'State', 'station': 'Station'});
        select_values = this._createSelect('weather-values-type',
            {'temp': 'Temperature', 'rain': 'Rainfall'});

        this._container.appendChild(select_raster);
        this._container.appendChild(select_values);

        // TODO: gfs/dwd text
        var input_forecast_flag;
        input_forecast_flag = document.createElement('input');
        input_forecast_flag.type = 'checkbox';
        input_forecast_flag.className = 'weather-forecast-flag';
        input_forecast_flag.defaultChecked = false;
        this._container.appendChild(input_forecast_flag);

        var input_date;
        input_date = this._createDatePicker("weather-date");
        this._container.appendChild(input_date);

        // TODO: Slider


        // TODO: Events with Leaflet
        $(this._container).on('change', null, this, this._onChange);


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
        $(this._container).off('change', null, this._onChange);
        map.removeLayer(this._layer);
    },

    // Fired by jQuery: calls _update in the context of the correct object
    _onChange: function(event) {
        var that = event.data;
        that._update();
    },

    // Called whenever the config changes and the correct geometry has to be displayed
    _update: function() {
        var url;
        url = this.getURL();

        this.color = ["#ff0000", "#00ff00", "#0000ff "][Math.floor(Math.random()*2.99)];
        console.log(url, this.color);
        this._layer.refresh(url);
    },

    // Return a closured style function, which has access to _this_.
    _getStyle: function() {
        var that = this;
        return (function(feature) {
            return {
                color: that.color
            }
        });
    },

    // Get the current config from the html input fields
    getConfig: function() {
        // TODO: think about jquery and stuff
        var container = this._container;

        var date = Date.parseDate($('#weather-date', container).val(),
                                  this._dateFormat);

        return {
            raster: $('#weather-raster-type', container).val(),
            values: $('#weather-values-type', container).val(),
            forecast: $(".weather-forecast-flag", container).prop("checked"),
            date: date,
            hour: '00' // TODO: slider missing
        };
    },

    // Get the URL for the current config
    getURL: function() {
        var config, url;
        config = this.getConfig();

        if (config.forecast) {
            url =  "forecast"
                    + "/" + config.raster
                    + "/" + config.date.dateFormat("YmdH")
                    + "/" + config.hour
                    + ".json";
        } else {
            url =  "observation"
                    + "/" + config.raster
                    + "/" + config.date.dateFormat("YmdH")
                    + ".json";
        }

        // TODO: baseurl
        var baseurl = "/";

        return baseurl + url;
    },

    // Create a select element with the given name and the key: value pairs as options
    _createSelect: function(name, options) {
        var select, key, name, option;

        select = document.createElement('select');
        select.setAttribute('id', name);
        select.setAttribute('name', name);
        select.setAttribute('class', name);

        for (key in options) {
            name = options[key];

            option = document.createElement('option');
            option.setAttribute('value', key);
            option.innerHTML = name;

            select.appendChild(option);
        }

        return select;
    },

    // Create an input element, which is handled by a jquery datetimepicker
    // TODO: replace by html5 <input type=date> and an additional hour field
    _createDatePicker: function(name) {
        var input;

        input = document.createElement('input');
        input.setAttribute('id', name);
        input.setAttribute('name', name);
        input.setAttribute('class', name);

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
            allowTimes: ['00:00', '06:00', '12:00', '18:00'],
            formatTime: 'H:i',
            // allowTimes: ['00', '06', '12', '18'],
            scrollTime: false
        });

        return input;
    }




});

L.control.weather = function (options) {
	return new L.Control.weather(options);
};