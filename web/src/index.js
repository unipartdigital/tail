import React, { useState } from 'react';
import ReactDOM from 'react-dom';
import {
  BrowserRouter as Router,
  Link,
  Redirect,
  Route,
  Switch,
} from 'react-router-dom';
import {
  Collapse,
  Container,
  Nav,
  Navbar,
  NavbarBrand,
  NavbarToggler,
  NavItem,
  NavLink,
} from 'reactstrap';
import { PanZoom } from 'react-easy-panzoom';
import styled, { keyframes } from 'styled-components';
import floorplan from './floorplan.svg';
import logo from './logo.svg';
import 'bootstrap/dist/css/bootstrap.css';

const LogoImage = styled.img.attrs(props => ({
  className: "mr-2",
}))`
  width: 1em;
`;

const tagAnimation = keyframes`
  0% {
    opacity: 1.00;
  }
  50% {
    opacity: 0.50;
  }
  100% {
    opacity: 1.00;
  }
`;

function TagDot(props) {

  const { x, y, r, color, ...other } = props;

  return (
    <circle cx={x} cy={y} r={r} fill={color} {...other}>
      <animate attributeType="XML" attributeName="r" from={r} to={r * 0.8}
               dur="1s" repeatCount="indefinite"/>
      <animate attributeType="XML" attributeName="opacity" from="1.0" to="0.5"
               dur="1s" repeatCount="indefinite"/>
    </circle>
  );
}

class TagMap extends React.Component {

  constructor(props) {
    super(props);
    this.panzoom = React.createRef();
    this.floorplan = React.createRef();
    this.onFloorplanLoad = this.onFloorplanLoad.bind(this);
  }

  onFloorplanLoad() {
    this.panzoom.current.autoCenter();
  }

  render() {

    let tagdots = this.props.tags.map((tag) => (
      <TagDot key={tag.id} id={tag.id} x={tag.x} y={tag.y} r={tag.r}
              color={tag.color}/>
    ));

    return (
      <PanZoom ref={this.panzoom}>
        <svg viewBox="0 0 1010 830">
          {tagdots}
          <image ref={this.floorplan} width="100%" height="100%"
                 xlinkHref={floorplan} onLoad={this.onFloorplanLoad}/>
        </svg>
      </PanZoom>
    );
  }
}

function TagList(props) {

  let tagrows = props.tags.map((tag) => (
    <tr key={tag.id}>
      <td>{tag.id}</td>
      <td>{tag.name}</td>
      <td>{tag.x}</td>
      <td>{tag.y}</td>
    </tr>
  ));

  return (
    <table width="100%">
      <thead>
        <tr>
          <th>ID</th>
          <th>Name</th>
          <th>X</th>
          <th>Y</th>
        </tr>
      </thead>
      <tbody>
        {tagrows}
      </tbody>
    </table>
  );
}

function Navigation() {

  const [navOpen, setNavOpen] = useState(false);

  const toggleNavOpen = () => setNavOpen(!navOpen);

  return (
    <Navbar color="light" light expand="md">
      <NavbarBrand href="/">
        <LogoImage src={logo}/>
        Tail Demo
      </NavbarBrand>
      <NavbarToggler onClick={toggleNavOpen}/>
      <Collapse isOpen={navOpen} navbar>
        <Nav className="ml-auto" navbar>
          <NavItem>
            <NavLink tag={Link} to="/map">Map</NavLink>
          </NavItem>
          <NavItem>
            <NavLink tag={Link} to="/list">List</NavLink>
          </NavItem>
        </Nav>
      </Collapse>
    </Navbar>
  );
}

function App() {

  const tags = [
    {
      "id": "70b3d5b1e0000139",
      "name": "YORK-871612",
      "x": 500,
      "y": 400,
      "r": 15,
      "color": "orange",
    },
    {
      "id": "70b3d5b1e0000145",
      "name": "YORK-456198",
      "x": 200,
      "y": 300,
      "r": 15,
      "color": "blue",
    },
  ];

  return (
    <div>
      <Router>
        <Navigation/>
        <Container>
          <Switch>
            <Redirect exact from="/" to="/map" component={TagMap}/>
            <Route path="/map"><TagMap tags={tags}/></Route>
            <Route path="/list"><TagList tags={tags}/></Route>
          </Switch>
        </Container>
      </Router>
    </div>
  );
}

ReactDOM.render(<App/>, document.getElementById('root'));
