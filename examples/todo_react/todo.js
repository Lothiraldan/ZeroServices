/** @jsx React.DOM */
var TodoItem = React.createClass({
    componentDidMount: function() {
        $.get("http://localhost:5001/todo_item/" + this.props.ressource_id + '/', function(result) {
          if (this.isMounted()) {
            this.setState(JSON.parse(result));
          }
        }.bind(this));
    },

    render: function() {
        return (
          <li>{this.props.ressource_id}</li>
        );
    }
})

var TodoList = React.createClass({
    handleSubmit: function(e) {
        e.preventDefault();
        var new_item_name = this.refs[this.props.ressource_id + '_new_item_name'].getDOMNode().value.trim();
        this.refs[this.props.ressource_id + '_new_item_name'].getDOMNode().value = '';

        // Create new item
        $.ajax({
            url: "http://localhost:5001/todo_item/" + new_item_name + "/",
            type: "POST",
            data: JSON.stringify({"ressource_data": {}}),
            dataType: "json",
            beforeSend: function(x) {
                if (x && x.overrideMimeType) {
                  x.overrideMimeType("application/j-son;charset=UTF-8");
                }
            },
        });

        // Link it
        $.ajax({
            url: "http://localhost:5001/todo_list/" + this.props.ressource_id + "/",
            type: "POST",
            headers: {
                "X-CUSTOM-ACTION": "add_link",
            },
            data: JSON.stringify({"relation": 'children', 'target_id': ['todo_item', new_item_name], 'title': 'Item'}),
            dataType: "json",
            beforeSend: function(x) {
                if (x && x.overrideMimeType) {
                  x.overrideMimeType("application/j-son;charset=UTF-8");
                }
            },
        });
    },

    render: function() {
        var links = this.props.ressource_data._links || {'children': []};

        return (
          <div>
            <h3>{this.props.ressource_id} list</h3>
            <ul>
                {links.children.map(function(link) {
                    return <TodoItem key={link.target_id[1]} ressource_id={link.target_id[1]} />
                })}
            </ul>
            <form onSubmit={this.handleSubmit}>
              <input ref={this.props.ressource_id + '_new_item_name'}/>
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
        var result_lists = JSON.parse(result);
        for(i in result_lists) {
          lists[result_lists[i].ressource_id] = result_lists[i];
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
        var resource = lists[evt.data.ressource_id].ressource_data;
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
        if(evt.data.ressource_name == 'todo_list') {
            // Register to resource events
            this.register_ressource_event(evt.data.ressource_id);

            // Add list
            var lists = this.state.lists;
            lists[evt.data.ressource_id] = evt.data;
            this.setState({'lists': lists});
        }
    }
  },

  register_ressource_event: function(ressource_id) {
    this.sock.send(JSON.stringify({'name': 'join', 'data':
      {'topic': 'todo_list.add_link.' + ressource_id}}));
    this.sock.send(JSON.stringify({'name': 'join', 'data':
      {'topic': 'todo_list.patch.' + ressource_id}}));
    this.sock.send(JSON.stringify({'name': 'join', 'data':
      {'topic': 'todo_list.delete.' + ressource_id}}));
  },

  on_connect: function() {
    this.sock.send(JSON.stringify({'name': 'join', 'data':
        {'topic': 'todo_list.create'}}));

    for(i in this.state.lists) {
      // Register to already retrieved resources events
      this.register_ressource_event(this.state.lists[i].ressource_id);
    }
  },

  handleNewList: function(e) {
    e.preventDefault();
    var new_list_name = this.refs.new_list_name.getDOMNode().value.trim();
    this.refs.new_list_name.getDOMNode().value = '';
    $.ajax({
        url: "http://localhost:5001/todo_list/" + new_list_name + "/",
        type: "POST",
        data: JSON.stringify({"ressource_data": {}}),
        dataType: "json",
        beforeSend: function(x) {
            if (x && x.overrideMimeType) {
              x.overrideMimeType("application/j-son;charset=UTF-8");
            }
        },
    });
  },

  render: function() {

    var lists = [];
    for(list_id in this.state.lists) {
      var list = this.state.lists[list_id];
      lists.push(<TodoList key={list.ressource_id} ressource_id={list.ressource_id} ressource_data={list.ressource_data} />)
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
