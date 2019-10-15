const HtmlWebpackPlugin = require('html-webpack-plugin');

module.exports = {
  entry: {
    index: __dirname + '/src/index.js',
  },
  output: {
    path: __dirname + '/dist',
    publicPath: '/dist/',
    filename: '[name].bundle.js',
  },
  module: {
    rules: [
      {
        test: /\.(js|jsx)$/,
        exclude: /node_modules/,
        use: [
	  { loader: 'babel-loader' },
	],
      },
      {
	test: /\.css$/,
	use: [
	  { loader: 'style-loader' },
	  { loader: 'css-loader' },
	],
      },
      {
	test: /\.(png|ttf|eot|svg|woff)/,
	use: [
	  { loader: 'file-loader' },
	],
      },
    ],
  },
  plugins: [
    new HtmlWebpackPlugin({
      title: 'Tail Demo',
      template: __dirname + '/src/index.html',
    }),
  ],
};
