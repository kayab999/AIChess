/* pieces.js — Piezas paramétricas FIDE en 4 estilos. Requiere THREE global.
 * Proporciones FIDE (rey=1.9): P 1.0, R 1.1, N 1.2, B 1.4, Q 1.7, K 1.9.
 * Estilos: clasico (Staunton madera), antiguo (Lewis marfil/rojo),
 *          cyberpunk (neón translúcido), wizard (piedra rúnica).
 */
(function (global) {
  'use strict';

  var DIMS = {
    p: { h: 1.00, r: 0.20 }, r: { h: 1.10, r: 0.22 }, n: { h: 1.20, r: 0.24 },
    b: { h: 1.40, r: 0.26 }, q: { h: 1.70, r: 0.32 }, k: { h: 1.90, r: 0.36 }
  };

  var STYLES = {
    clasico:   { chunky: 1.0,  short: 1.0,  wire: false, glow: false,
                 board: [0x8f5f33, 0xe6c88f], spark: false },
    antiguo:   { chunky: 1.28, short: 0.86, wire: false, glow: false,
                 board: [0x9a7d55, 0xd9c9a8], spark: false, slabPawns: true },
    cyberpunk: { chunky: 0.92, short: 1.02, wire: true,  glow: true,
                 board: [0x0a1628, 0x12314e], spark: false, grid: true },
    wizard:    { chunky: 1.1,  short: 0.95, wire: false, glow: true,
                 board: [0x2c2f3a, 0x565b6b], spark: true }
  };

  function styleDef(name) {
    return STYLES[name] || STYLES.clasico;
  }

  function bodyMaterial(style, color) {
    if (style === 'cyberpunk') {
      return new THREE.MeshStandardMaterial({
        color: color === 'w' ? 0x06283a : 0x2b0a2e,
        emissive: color === 'w' ? 0x0aa8c8 : 0xc80a9a,
        emissiveIntensity: 0.25, transparent: true, opacity: 0.82,
        roughness: 0.25, metalness: 0.6
      });
    }
    if (style === 'wizard') {
      return new THREE.MeshStandardMaterial({
        color: color === 'w' ? 0x8f9bb0 : 0x3a3f52,
        emissive: 0x6a2fd8, emissiveIntensity: 0.12,
        roughness: 0.85, metalness: 0.15
      });
    }
    if (style === 'antiguo') {
      return new THREE.MeshStandardMaterial({
        color: color === 'w' ? 0xe9dcc0 : 0x8e2f26,
        roughness: 0.9, metalness: 0.0
      });
    }
    return new THREE.MeshStandardMaterial({
      color: color === 'w' ? 0xe6c88f : 0x4a2c14,
      roughness: 0.55, metalness: 0.05
    });
  }

  function trimMaterial(style, color) {
    if (style === 'cyberpunk') {
      return new THREE.MeshBasicMaterial({
        color: color === 'w' ? 0x35e0ff : 0xff35c8 });
    }
    if (style === 'wizard') {
      return new THREE.MeshStandardMaterial({
        color: 0x6a2fd8, emissive: 0x6a2fd8, emissiveIntensity: 0.8 });
    }
    return bodyMaterial(style, color);
  }

  /* Cuerpo torneado: base -> pie -> fuste -> collarines -> cuello. */
  function latheBody(h, r, mat, chunky) {
    var R = r * chunky, pts = [], y;
    function ring(radius, yy) { pts.push(new THREE.Vector2(Math.max(radius, 0.001), yy)); }
    ring(R, 0);
    ring(R, 0.03 * h);
    ring(R * 0.82, 0.06 * h);
    ring(R * 0.60, 0.10 * h);
    ring(R * 0.46, 0.16 * h);
    ring(R * 0.40, 0.30 * h);
    ring(R * 0.44, 0.42 * h);   // collar bajo
    ring(R * 0.44, 0.46 * h);
    ring(R * 0.36, 0.50 * h);
    ring(R * 0.32, 0.62 * h);
    ring(R * 0.38, 0.70 * h);   // collar alto
    ring(R * 0.38, 0.74 * h);
    ring(R * 0.30, 0.78 * h);
    y = 0.78 * h;
    var geo = new THREE.LatheGeometry(pts, 40);
    var mesh = new THREE.Mesh(geo, mat);
    mesh.userData.topY = y;
    mesh.userData.topR = R * 0.30;
    return mesh;
  }

  function ball(r, mat) {
    return new THREE.Mesh(new THREE.SphereGeometry(r, 24, 18), mat);
  }

  /* Remates por pieza. Devuelve Group anclado en (0, topY, 0). */
  function topper(type, topY, topR, mat, trim, style) {
    var g = new THREE.Group(), m;
    if (type === 'p') {
      if (style === 'antiguo') {  // losa geométrica Lewis
        m = new THREE.Mesh(new THREE.BoxGeometry(topR * 1.6, topR * 2.2, topR * 0.7), mat);
        m.position.y = topR * 1.1; g.add(m);
      } else {
        m = ball(topR * 1.15, mat); m.position.y = topR * 1.05; g.add(m);
      }
    } else if (type === 'r') {
      var wall = new THREE.Mesh(new THREE.CylinderGeometry(topR * 1.15, topR * 1.05, topR * 0.9, 24), mat);
      wall.position.y = topR * 0.45; g.add(wall);
      for (var i = 0; i < 4; i++) {  // almenas
        var c = new THREE.Mesh(new THREE.BoxGeometry(topR * 0.5, topR * 0.45, topR * 0.3), mat);
        var a = i * Math.PI / 2;
        c.position.set(Math.cos(a) * topR * 0.95, topR * 1.05, Math.sin(a) * topR * 0.95);
        c.rotation.y = -a; g.add(c);
      }
    } else if (type === 'n') {
      var neck = new THREE.Mesh(new THREE.CylinderGeometry(topR * 0.55, topR * 0.8, topR * 2.2, 16), mat);
      neck.position.set(0, topR * 1.0, -topR * 0.25); neck.rotation.x = 0.35; g.add(neck);
      var head = new THREE.Mesh(new THREE.ConeGeometry(topR * 0.62, topR * 1.7, 4), mat);
      head.position.set(0, topR * 2.0, topR * 0.35); head.rotation.x = 1.25; g.add(head);
      [-1, 1].forEach(function (s) {
        var ear = new THREE.Mesh(new THREE.ConeGeometry(topR * 0.16, topR * 0.5, 6), style === 'wizard' ? trim : mat);
        ear.position.set(s * topR * 0.3, topR * 2.75, -topR * 0.15); g.add(ear);
      });
    } else if (type === 'b') {
      var bulb = new THREE.Mesh(new THREE.SphereGeometry(topR * 1.05, 24, 18), mat);
      bulb.scale.y = 1.5; bulb.position.y = topR * 1.3;
      if (style === 'wizard') {  // gorro de mago
        var hat = new THREE.Mesh(new THREE.ConeGeometry(topR * 0.95, topR * 2.4, 20), mat);
        hat.position.y = topR * 2.2; hat.rotation.z = 0.12; g.add(hat);
        var tip = ball(topR * 0.22, trim); tip.position.set(-topR * 0.28, topR * 3.35, 0); g.add(tip);
      } else {
        g.add(bulb);
        var tipB = ball(topR * 0.28, mat); tipB.position.y = topR * 2.95; g.add(tipB);
      }
    } else if (type === 'q') {
      var band = new THREE.Mesh(new THREE.CylinderGeometry(topR * 1.1, topR * 0.9, topR * 0.5, 24), mat);
      band.position.y = topR * 0.25; g.add(band);
      for (var k = 0; k < 6; k++) {  // corona de puntas
        var spike = new THREE.Mesh(new THREE.ConeGeometry(topR * 0.16, topR * 0.7, 6), style === 'wizard' ? trim : mat);
        var aa = k * Math.PI / 3;
        spike.position.set(Math.cos(aa) * topR * 0.95, topR * 0.75, Math.sin(aa) * topR * 0.95);
        g.add(spike);
      }
      var orb = ball(topR * 0.4, trim); orb.position.y = topR * 0.9; g.add(orb);
    } else if (type === 'k') {
      var dome = new THREE.Mesh(new THREE.SphereGeometry(topR * 1.0, 24, 16, 0, Math.PI * 2, 0, Math.PI / 2), mat);
      dome.position.y = 0; g.add(dome);
      var v = new THREE.Mesh(new THREE.BoxGeometry(topR * 0.28, topR * 1.3, topR * 0.28), style === 'wizard' ? trim : mat);
      v.position.y = topR * 1.5; g.add(v);
      var hbar = new THREE.Mesh(new THREE.BoxGeometry(topR * 0.85, topR * 0.28, topR * 0.28), style === 'wizard' ? trim : mat);
      hbar.position.y = topR * 1.55; g.add(hbar);
    }
    g.position.y = topY;
    return g;
  }

  function makePiece(type, color, styleName) {
    var def = styleDef(styleName), d = DIMS[type];
    var h = d.h * def.short, mat = bodyMaterial(styleName, color);
    var group = new THREE.Group();
    var body = latheBody(h, d.r, mat, def.chunky);
    group.add(body);
    var trim = trimMaterial(styleName, color);
    group.add(topper(type, body.userData.topY, body.userData.topR, mat, trim, styleName));
    if (def.wire) {  // overlay de aristas neón (cyberpunk)
      var wire = new THREE.Mesh(body.geometry,
        new THREE.MeshBasicMaterial({ color: color === 'w' ? 0x35e0ff : 0xff35c8, wireframe: true, transparent: true, opacity: 0.35 }));
      wire.scale.set(1.002, 1.002, 1.002);
      group.add(wire);
    }
    group.userData = { type: type, color: color, style: styleName, height: h };
    return group;
  }

  function squareColors(styleName) {
    return styleDef(styleName).board;
  }

  global.AICHESS_PIECES = {
    makePiece: makePiece, squareColors: squareColors,
    STYLES: Object.keys(STYLES), DIMS: DIMS
  };
})(typeof window !== 'undefined' ? window : this);
