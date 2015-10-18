var path = require('path')
var webpack = require('webpack')
var WebpackDevServer = require('webpack-dev-server')

var config = {
  devtool: 'cheap-module-eval-source-map',
  entry: [
    'webpack-dev-server/client?http://localhost:3333',
    'webpack/hot/only-dev-server',
    './app.jsx'
  ],
  output: {
    filename: 'bundle.js',
    path: __dirname,
    publicPath: ''
  },
  plugins: [
    new webpack.HotModuleReplacementPlugin(),
    new webpack.NoErrorsPlugin()
  ],
  resolve: {
    extensions: ['', '.js', '.jsx'],
    // Tell webpack to look for required files in bower and node
    modulesDirectories: ['bower_components', 'node_modules']
  },
  module: {
    loaders: [
      {
        test: /\.jsx?$/,
        loaders: ['react-hot', 'babel?optional[]=runtime&stage=0'],
        include: path.join(__dirname, 'app')
      },
      {
        test: /\.css$/, loader: "style-loader!css-loader"
      },
      { test: /\.woff(\?v=\d+\.\d+\.\d+)?$/, loader: "url?limit=10000&minetype=application/font-woff" },
      { test: /\.woff2(\?v=\d+\.\d+\.\d+)?$/, loader: "url?limit=10000&minetype=application/font-woff" },
      { test: /\.ttf(\?v=\d+\.\d+\.\d+)?$/, loader: "url?limit=10000&minetype=application/octet-stream" },
      { test: /\.eot(\?v=\d+\.\d+\.\d+)?$/, loader: "file" },
      { test: /\.svg(\?v=\d+\.\d+\.\d+)?$/, loader: "url?limit=10000&minetype=image/svg+xml" },
      { test: /\.jpg$/, loader: "file" },
      { test: /\.png$/, loader: "file" },
    ]
  }
}

new WebpackDevServer(webpack(config), {
  publicPath: config.output.publicPath,
  hot: true,
  historyApiFallback: true
}).listen(3333, 'localhost', function (err, result) {
  if (err) {
    console.log(err)
  }

  console.log('Listening at localhost:3333')
})
