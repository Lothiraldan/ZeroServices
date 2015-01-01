/** @jsx React.DOM */
var TodoItem = React.createClass({
    componentDidMount: function() {
        $.get("http://localhost:5001/todo_item/" + this.props.resource_id + '/', function(result) {
          if (this.isMounted()) {
            this.setState(result);
          }
        }.bind(this));
    },

    render: function() {
        return (
          <li>{this.props.resource_id}</li>
        );
    }
})

var TodoList = React.createClass({
    handleSubmit: function(e) {
        e.preventDefault();
        var new_item_name = this.refs[this.props.resource_id + '_new_item_name'].getDOMNode().value.trim();
        this.refs[this.props.resource_id + '_new_item_name'].getDOMNode().value = '';

        // Create new item
        $.ajax({
            url: "http://localhost:5001/todo_item/" + new_item_name + "/",
            type: "POST",
            data: JSON.stringify({"resource_data": {}}),
            dataType: "json",
            beforeSend: function(x) {
                if (x && x.overrideMimeType) {
                  x.overrideMimeType("application/json;charset=UTF-8");
                }
            },
        });

        // Link it
        $.ajax({
            url: "http://localhost:5001/todo_list/" + this.props.resource_id + "/",
            type: "POST",
            headers: {
                "X-CUSTOM-ACTION": "add_link",
            },
            data: JSON.stringify({"relation": 'children', 'target_id': ['todo_item', new_item_name], 'title': 'Item'}),
            dataType: "json",
            beforeSend: function(x) {
                if (x && x.overrideMimeType) {
                  x.overrideMimeType("application/json;charset=UTF-8");
                }
            },
        });
    },

    render: function() {
        var links = this.props.resource_data._links || {'children': []};

        return (
          <div>
            <h3>{this.props.resource_id} list</h3>
            <ul>
                {links.children.map(function(link) {
                    return <TodoItem key={link.target_id[1]} resource_id={link.target_id[1]} />
                })}
            </ul>
            <form onSubmit={this.handleSubmit}>
              <input ref={this.props.resource_id + '_new_item_name'}/>
              <button>{'Add #' + (links.children.length + 1)}</button>
            </form>
          </div>
        );
    }
})

var TodoApp = React.createClass({
  getInitialState: function() {
    this.sock = new SockReconnect('http://localhost:5001/realtime', null, null, this.onmessage, this.on_connect);
    this.sock.connect();

    return {'lists': {}, 'items': {}};
  },

  componentDidMount: function() {
    $.get("http://localhost:5001/todo_list/", function(result) {
      if (this.isMounted()) {
        var lists = {};
        var result_lists = result;
        for(i in result_lists) {
          lists[result_lists[i].resource_id] = result_lists[i];
        }
        this.setState({'lists': lists});
      }
    }.bind(this));
  },

  onmessage: function(evt) {
    var evt = evt.data;
    if(evt.data.action == 'patch') {
      this.update(evt.data.data.patch['$set']);
    }
    else if(evt.data.action == 'add_link') {
        var lists = this.state.lists;
        var resource = lists[evt.data.resource_id].resource_data;
        if (resource._links == undefined) {
          resource._links = {};
        }
        var links = resource._links;
        if(links[evt.data.relation] == undefined) {
          links[evt.data.relation] = [];
        }
        links[evt.data.relation].push({'title': evt.data.title, 'target_id': evt.data.target_id});
        this.setState({'lists': lists});
    }
    else if(evt.data.action == 'create') {
        if(evt.data.resource_name == 'todo_list') {
            // Register to resource events
            this.register_resource_event(evt.data.resource_id);

            // Add list
            var lists = this.state.lists;
            lists[evt.data.resource_id] = evt.data;
            this.setState({'lists': lists});
        }
    }
  },

  register_resource_event: function(resource_id) {
    this.sock.send(JSON.stringify({'name': 'join', 'data':
      {'topic': 'todo_list.add_link.' + resource_id}}));
    this.sock.send(JSON.stringify({'name': 'join', 'data':
      {'topic': 'todo_list.patch.' + resource_id}}));
    this.sock.send(JSON.stringify({'name': 'join', 'data':
      {'topic': 'todo_list.delete.' + resource_id}}));
  },

  on_connect: function() {
    this.sock.send(JSON.stringify({'name': 'join', 'data':
        {'topic': 'todo_list.create'}}));

    for(i in this.state.lists) {
      // Register to already retrieved resources events
      this.register_resource_event(this.state.lists[i].resource_id);
    }
  },

  handleNewList: function(e) {
    e.preventDefault();
    var new_list_name = this.refs.new_list_name.getDOMNode().value.trim();
    this.refs.new_list_name.getDOMNode().value = '';
    $.ajax({
        url: "http://localhost:5001/todo_list/" + new_list_name + "/",
        type: "POST",
        data: JSON.stringify({"resource_data": {}}),
        dataType: "json",
        beforeSend: function(x) {
            if (x && x.overrideMimeType) {
              x.overrideMimeType("application/json;charset=UTF-8");
            }
        },
    });
  },

  render: function() {

    var lists = [];
    for(list_id in this.state.lists) {
      var list = this.state.lists[list_id];
      lists.push(<TodoList key={list.resource_id} resource_id={list.resource_id} resource_data={list.resource_data} />)
    }

    return (
        <div>
            <form onSubmit={this.handleNewList}>
              <input ref="new_list_name" />
              <button>{'New list'}</button>
            </form>

            {lists}

        </div>
    );
  }
});

React.render(<TodoApp />, document.body);
