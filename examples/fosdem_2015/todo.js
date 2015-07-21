/** @jsx React.DOM */
var Power = React.createClass({

    render: function() {
        return (
          <div>
            <h2>{this.props.resource_id} power</h2>
            <h3>Description: {this.props.resource_data.description}</h3>
            <h3>Status: {this.props.resource_data.status}</h3>
            <h3>Value: {this.props.resource_data.value}</h3>
            <h3>Result: {this.props.resource_data.result}</h3>
          </div>
        );
    }
});

var TodoApp = React.createClass({
  getInitialState: function() {
    this.sock = new WebSocket('ws://localhost:5001/realtime');
    this.sock.onmessage = this.onmessage;
    this.sock.onopen = this.on_connect;

    return {'power': {}};
  },


  componentDidMount: function() {
    $.get("http://localhost:5001/power/", function(result) {
      if (this.isMounted()) {
        var lists = {};
        for(i in result) {
          lists[result[i].resource_id] = result[i];
        }
        this.setState({'power': lists});
      }
    }.bind(this));
  },

  onmessage: function(evt) {
    console.log("EVT" + evt);
    var evt = JSON.parse(evt.data);
    console.log(evt);
    if(evt.data.action == 'patch') {
        var lists = this.state.power;
        var resource = lists[evt.data.resource_id].resource_data;

        for (var attrname in evt.data.patch['$set']) {
          resource[attrname] = evt.data.patch['$set'][attrname];
        }

        lists[evt.data.resource_id].resource_data = resource;
        console.log(lists);
        this.setState({'power': lists});
    }
    else if(evt.data.action == 'add_link') {
        var lists = this.state.power;
        var resource = lists[evt.data.resource_id].resource_data;
        if (resource._links == undefined) {
          resource._links = {};
        }
        var links = resource._links;
        if(links[evt.data.relation] == undefined) {
          links[evt.data.relation] = [];
        }
        links[evt.data.relation].push({'title': evt.data.title, 'target_id': evt.data.target_id});
        this.setState({'power': lists});
    }
    else if(evt.data.action == 'create') {
        if(evt.data.resource_name == 'power') {
            // Register to resource events
            this.register_resource_event(evt.data.resource_id);

            // Add list
            var lists = this.state.power;
            lists[evt.data.resource_id] = evt.data;
            this.setState({'power': lists});
        }
    }
  },

  register_resource_event: function(resource_id) {
    topics = ['power.add_link.' + resource_id, 'power.patch.' + resource_id,
              'power.delete.' + resource_id];
    this.sock.send(JSON.stringify({'type': 'subscribe', 'data': {'topics': topics}}));
  },

  on_connect: function() {
    console.log('on connect');
    this.sock.send(JSON.stringify({'type': 'join', 'data':
        {'topics': ['power.create']}}));

    for(i in this.state.power) {
      // Register to already retrieved resources events
      this.register_resource_event(this.state.power[i].resource_id);
    }
  },

  render: function() {

    var lists = [];
    for(list_id in this.state.power) {
      var list = this.state.power[list_id];
      lists.push(<li><Power key={list.resource_id} resource_id={list.resource_id} resource_data={list.resource_data} /></li>)
    }

    return (
        <div>
            <h1>Resources:</h1>
            <ul>
              {lists}
            </ul>

        </div>
    );
  }
});

React.render(<TodoApp />, document.body);
