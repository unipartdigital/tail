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
import styled from 'styled-components';
import floorplan from './floorplan.svg';
import logo from './logo.svg';
import 'bootstrap/dist/css/bootstrap.css';

const LogoImage = styled.img.attrs(props => ({
  className: "mr-2",
}))`
  width: 1em;
`;

const FloorplanImage = styled.img`
  width: 100%;
  pointer-events: none;
`;

function TagMap() {

  return (
    <PanZoom>
      <FloorplanImage src={floorplan}/>
    </PanZoom>
  );
}

function TagList() {

  return (
    <div>List of tags</div>
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

  return (
    <div>
      <Router>
        <Navigation/>
        <Container>
          <Switch>
            <Redirect exact from="/" to="/map" component={TagMap}/>
            <Route path="/map" component={TagMap}/>
            <Route path="/list" component={TagList}/>
          </Switch>
        </Container>
      </Router>
    </div>
  );
}

ReactDOM.render(<App/>, document.getElementById('root'));
