import React, { useEffect, useRef, useState } from 'react';
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
  Modal,
  ModalBody,
  Nav,
  Navbar,
  NavbarBrand,
  NavbarToggler,
  NavItem,
  NavLink,
  Spinner,
  Table,
} from 'reactstrap';
import { PanZoom } from 'react-easy-panzoom';
import useWebSocket from 'react-use-websocket';
import styled, { keyframes } from 'styled-components';
import floorplan from './floorplan.svg';
import logo from './logo.svg';
import 'bootstrap/dist/css/bootstrap.css';

var ws_url = new URL('/tags', window.location.href);
ws_url.protocol = ws_url.protocol.replace('http', 'ws');

const LogoImage = styled.img.attrs(props => ({
  className: "mr-2",
}))`
  width: 1em;
`;

const FloorplanObject = styled.object`
  pointer-events: none;
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

function TagDot({ x, y, r, color, ...other }) {
  return (
    <circle cx={x} cy={y} r={r} fill={color} {...other}>
      <animate attributeType="XML" attributeName="r" from={r} to={r * 0.8}
               dur="1s" repeatCount="indefinite"/>
      <animate attributeType="XML" attributeName="opacity" from="1.0" to="0.5"
               dur="1s" repeatCount="indefinite"/>
    </circle>
  );
}

function TagDots({tags, target}) {

  if (!target)
    return <div/>;

  const tagdots = Object.entries(tags).map(([id, {x, y, r, color}]) => (
    <TagDot key={id} id={id} x={x} y={y} r={r} color={color}/>
  ));

  return ReactDOM.createPortal(
    <g transform="scale(1,-1) translate(0,-5.35)">
      {tagdots}
    </g>,
    target
  );
}

function TagMap({tags}) {

  const panzoomRef = useRef();
  const floorplanRef = useRef();

  const onFloorplanLoad = () => {
    panzoomRef.current.autoCenter();
  };

  return (
    <PanZoom ref={panzoomRef}>
      <FloorplanObject ref={floorplanRef} data={floorplan} width="100%"
                       onLoad={onFloorplanLoad}/>
      <TagDots tags={tags}
               target={floorplanRef.current &&
                       floorplanRef.current.contentDocument &&
                       floorplanRef.current.contentDocument.documentElement}/>
    </PanZoom>
  );
}

function TagList({tags}) {

  const tagrows = Object.entries(tags).map(([id, {name, x, y}]) => (
    <tr key={id}>
      <td>{id}</td>
      <td>{name}</td>
      <td>{x.toFixed(2)}</td>
      <td>{y.toFixed(2)}</td>
    </tr>
  ));

  return (
    <Table striped width="100%">
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
    </Table>
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

  const [tags, setTags] = useState({});
  const [sendMessage, lastMessage, readyState] = useWebSocket(ws_url.href);

  useEffect(() => {
    if (lastMessage !== null) {
      const newTags = JSON.parse(lastMessage.data);
      setTags(prevTags => ({...prevTags, ...newTags}));
    }
  }, [lastMessage]);

  return (
    <div>
      <Router>
        <Modal isOpen={readyState != 1}>
          <ModalBody>
            <Spinner size="sm"/>
            {' '}
            Connecting...
          </ModalBody>
        </Modal>
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
