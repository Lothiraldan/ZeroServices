/** @jsx React.DOM */
var TodoList = React.createClass({
  createItem: function(itemText) {
      return <li>{itemText} [<a href="#" onClick={this.props.handleDelete.bind(this, itemText)}>x</a>]</li>;
  },

  render: function() {
    return <ul>{this.props.items.map(this.createItem)}</ul>;
  }
});


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
    getInitialState: function() {
        return {'ressource_data': {}}
    },

    componentDidMount: function() {
        console.log("Props id", this.props.ressource_id);
        $.get("http://localhost:5001/todo_list/" + this.props.ressource_id + '/', function(result) {
          if (this.isMounted()) {
            this.setState(JSON.parse(result));
          }
        }.bind(this));
    },

    handleSubmit: function(e) {
        e.preventDefault();
        var new_item_name = this.refs[this.props.ressource_id + '_new_item_name'].getDOMNode().value.trim();
        console.log(new_item_name);
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
            url: "http://localhost:5001/todo_list/" + this.state.ressource_id + "/",
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
        var links = this.state.ressource_data._links || {'children': []};

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

    return {'lists': []};
  },

  componentDidMount: function() {
    $.get("http://localhost:5001/todo_list/", function(result) {
      if (this.isMounted()) {
        this.setState({'lists': JSON.parse(result)});
      }
    }.bind(this));
  },

  onmessage: function(evt) {
    var evt = evt.data;
    if(evt.data.action == 'patch') {
      this.update(evt.data.data.patch['$set']);
      }
    else if(evt.data.action == 'add_link') {
        console.log('Add link??');
        this.add_link(evt.data.data);
    }
    else if(evt.data.action == 'create') {
        if(evt.data.ressource_name == 'todo_list') {
            var lists = this.state.lists;
            ressource = evt.data.ressource_data;
            ressource['ressource_id'] = evt.data.ressource_id;
            lists.push(ressource);
            this.setState({'lists': lists});
        }
    }
    },

  on_connect: function() {
    console.log("Send???")
    this.sock.send(JSON.stringify({'name': 'join', 'data':
        {'topic': 'todo_list.create'}}));
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
    return (
        <div>
            <form onSubmit={this.handleNewList}>
              <input ref="new_list_name" />
              <button>{'New list'}</button>
            </form>

            {this.state.lists.map(function(list) {
                return <TodoList key={list.ressource_id} ressource_id={list.ressource_id} />
            })}

        </div>
    );
  }
});

React.render(<TodoApp />, document.body);
