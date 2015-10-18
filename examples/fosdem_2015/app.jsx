import React from 'react/addons';
import ReactDom from 'react-dom'
import Baobab from 'baobab'
import axios from 'axios';

// Style
import {bootstrap} from './bower_components/bootstrap/dist/css/bootstrap.css';

// Initialization
var tree = new Baobab({});

let onopen = function() {
  let subscribe_msg = {'type': 'join', 'data': {'topics': ['power']}}
  ws.send(JSON.stringify(subscribe_msg));
}

let onmessage = function(evt) {
  let data = JSON.parse(evt.data).data;
  let action = data.action;
  let resource_id = data.resource_id;
  if (action == 'patch') {
    let patch = data.patch['$set'];
    for(let key in patch) {
      tree.set([resource_id, key], patch[key]);
    }
  } else if (action == 'create') {
    tree.set(resource_id, data.resource_data);
  }
}

let onclose = function() {
  console.log("Close");
}

var ws = new WebSocket('ws://localhost:5001/realtime');
ws.onmessage = onmessage;
ws.onopen = onopen;
ws.onclose = onclose;

// Components
class Row extends React.Component {
  render() {

    let status = this.props.status;
    if(status == 'pending') {
      var klass = 'warning';
    } else {
      var klass = 'success';
    }

    return (
      <tr className={klass}>
        <td>{this.props.id}</td>
        <td>{this.props.value}</td>
        <td style={{minWidth: '100px'}}>{status}</td>
        <td>{this.props.result}</td>
      </tr>
    )
  }
}

class Table extends React.Component {

  render() {

    let rows = [];
    let resources = tree.get();
    for (let key in resources) {
        rows.push(<Row key={key} id={key} {...resources[key]}></Row>);
    }

    return (
      <div>
        <h1>Resources</h1>
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Value</th>
              <th>Status</th>
              <th>Result (value * value)</th>
            </tr>
          </thead>
          <tbody>
            {rows}
          </tbody>
        </table>
      </div>
    )
  }
}

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

let query = axios.get("http://localhost:5001/power").then(function(response) {
    let data = response.data;
    for(let key in data) {
      let resource_id = data[key].resource_id;
      let resource_data = data[key].resource_data;
      tree.set(resource_id, resource_data);
    }
});

var render = function() {
  ReactDom.render(<Table />, document.getElementById('content'));
}


tree.on('update', render);

render();
