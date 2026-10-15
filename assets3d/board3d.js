/* board3d.js — Escena Three.js: tablero, piezas FEN, replay animado, jaque y chispas.
 * Lee global AICHESS_DATA = {fen, movesUci[], style, checkSq, turn}.
 * Requiere THREE, OrbitControls y AICHESS_PIECES globales.
 */
(function (global) {
  'use strict';

  var SQ = 1;
  function sq2xz(sq) {  // 'e4' -> [x, z]
    return [(sq.charCodeAt(0) - 97) - 3.5, 3.5 - (parseInt(sq[1], 10) - 1)];
  }

  function parseFenPlacement(fen) {
    var rows = fen.split(' ')[0].split('/'), out = [];
    for (var r = 0; r < 8; r++) {
      var file = 0;
      for (var i = 0; i < rows[r].length; i++) {
        var c = rows[r][i];
        if (/\d/.test(c)) { file += parseInt(c, 10); continue; }
        out.push({ type: c.toLowerCase(),
                   color: c === c.toUpperCase() ? 'w' : 'b',
                   sq: String.fromCharCode(97 + file) + (8 - r) });
        file++;
      }
    }
    return out;
  }

  function applyUci(state, uci) {  // state: {sq: mesh}; devuelve {mesh, captured}
    var from = uci.slice(0, 2), to = uci.slice(2, 4), promo = uci[4] || null;
    var mesh = state[from];
    var captured = state[to] || null;
    // En passant: el peón capturado no está en 'to'.
    if (mesh && mesh.userData.type === 'p' && from[0] !== to[0] && !captured) {
      var epSq = to[0] + from[1];
      captured = state[epSq] || null;
      delete state[epSq];
    }
    delete state[from];
    state[to] = mesh;
    // Enroque: mueve también la torre.
    if (mesh && mesh.userData.type === 'k' && Math.abs(to.charCodeAt(0) - from.charCodeAt(0)) === 2) {
      var rank = from[1];
      var rf = to[0] > from[0] ? 'h' + rank : 'a' + rank;
      var rt = to[0] > from[0] ? 'f' + rank : 'd' + rank;
      if (state[rf]) { state[rt] = state[rf]; delete state[rf]; state[rt].userData.sq = rt;
        state[rt].userData.castleTo = rt; }
    }
    if (mesh) {
      mesh.userData.sq = to;
      if (promo) mesh.userData.promoteTo = promo;
    }
    return { mesh: mesh, captured: captured };
  }

  function init() {
    var DATA = global.AICHESS_DATA || {};
    var style = DATA.style || 'clasico';
    var mount = document.getElementById('scene');

    var renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    mount.appendChild(renderer.domElement);

    var scene = new THREE.Scene();
    scene.background = style === 'cyberpunk'
      ? new THREE.Color(0x030914)
      : new THREE.Color(0x0a1628);
    if (style === 'cyberpunk') scene.fog = new THREE.Fog(0x030914, 14, 26);

    var camera = new THREE.PerspectiveCamera(45,
      mount.clientWidth / mount.clientHeight, 0.1, 100);
    camera.position.set(0, 7.2, 9.2);

    var controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 0.4, 0);
    controls.enableDamping = true;
    controls.maxPolarAngle = Math.PI * 0.49;
    controls.minDistance = 4; controls.maxDistance = 22;

    scene.add(new THREE.HemisphereLight(0xbfd9ff, 0x1a1410, 0.75));
    var sun = new THREE.DirectionalLight(0xffffff, 0.9);
    sun.position.set(5, 10, 6);
    sun.castShadow = true;
    sun.shadow.mapSize.set(1024, 1024);
    sun.shadow.camera.left = -6; sun.shadow.camera.right = 6;
    sun.shadow.camera.top = 6; sun.shadow.camera.bottom = -6;
    scene.add(sun);
    if (style === 'cyberpunk' || style === 'wizard') {
      var accent = new THREE.PointLight(style === 'cyberpunk' ? 0x35e0ff : 0x6a2fd8, 0.9, 20);
      accent.position.set(-4, 3, -4);
      scene.add(accent);
    }

    // Tablero
    var cols = AICHESS_PIECES.squareColors(style);
    var lightM = new THREE.MeshStandardMaterial({ color: cols[0], roughness: 0.6 });
    var darkM = new THREE.MeshStandardMaterial({ color: cols[1], roughness: 0.6 });
    if (style === 'cyberpunk') {
      lightM.emissive = new THREE.Color(0x0a2a3a); lightM.emissiveIntensity = 0.7;
      darkM.emissive = new THREE.Color(0x06121f); darkM.emissiveIntensity = 0.7;
    }
    var sqGeo = new THREE.BoxGeometry(SQ, 0.22, SQ);
    for (var f = 0; f < 8; f++) for (var r = 0; r < 8; r++) {
      var cell = new THREE.Mesh(sqGeo, ((f + r) % 2 === 0) ? darkM : lightM);
      cell.position.set(f - 3.5, -0.11, r - 3.5);
      cell.receiveShadow = true;
      scene.add(cell);
    }
    var frame = new THREE.Mesh(new THREE.BoxGeometry(9.2, 0.3, 9.2),
      new THREE.MeshStandardMaterial({ color: style === 'cyberpunk' ? 0x06121f : 0x2a1a0e, roughness: 0.5 }));
    frame.position.y = -0.22; frame.receiveShadow = true; scene.add(frame);
    if (style === 'cyberpunk') {
      var grid = new THREE.GridHelper(24, 24, 0x35e0ff, 0x12314e);
      grid.position.y = -0.38;
      grid.material.transparent = true; grid.material.opacity = 0.5;
      scene.add(grid);
    }

    // Piezas desde la posición inicial; se animan las jugadas.
    var state = {};
    parseFenPlacement('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')
      .forEach(function (p) {
        var mesh = AICHESS_PIECES.makePiece(p.type, p.color, style);
        var xz = sq2xz(p.sq);
        mesh.position.set(xz[0], 0, xz[1]);
        mesh.traverse(function (o) { if (o.isMesh) o.castShadow = true; });
        mesh.userData.sq = p.sq;
        scene.add(mesh);
        state[p.sq] = mesh;
      });

    // Cola de animación: [{mesh, from:[x,z], to:[x,z], t, dur, captured, done}]
    var queue = [], clock = new THREE.Clock(), time = 0;
    var moves = DATA.movesUci || [];
    moves.forEach(function (uci, idx) {
      var res = applyUci(state, uci);
      if (!res.mesh) return;
      var a = sq2xz(uci.slice(0, 2)), b = sq2xz(uci.slice(2, 4));
      queue.push({ mesh: res.mesh, from: a, to: b, t: -idx * 0.55, dur: 0.5,
                   captured: res.captured, fade: 0,
                   promote: uci[4] || null, color: res.mesh.userData.color });
    });

    // Pulso de jaque
    var pulse = null;
    if (DATA.checkSq) {
      var px = sq2xz(DATA.checkSq);
      pulse = new THREE.Mesh(new THREE.PlaneGeometry(1, 1),
        new THREE.MeshBasicMaterial({ color: 0xff2244, transparent: true, opacity: 0.0 }));
      pulse.rotation.x = -Math.PI / 2;
      pulse.position.set(px[0], 0.005, px[1]);
      scene.add(pulse);
    }

    // Chispas wizard
    var sparks = null, sparkVel = [];
    if (style === 'wizard') {
      var N = 120, pos = new Float32Array(N * 3);
      for (var s = 0; s < N; s++) {
        pos[s * 3] = (Math.random() - 0.5) * 9;
        pos[s * 3 + 1] = Math.random() * 4;
        pos[s * 3 + 2] = (Math.random() - 0.5) * 9;
        sparkVel.push(0.2 + Math.random() * 0.5);
      }
      var sg = new THREE.BufferGeometry();
      sg.setAttribute('position', new THREE.BufferAttribute(pos, 3));
      sparks = new THREE.Points(sg, new THREE.PointsMaterial({
        color: 0x9a6bff, size: 0.06, transparent: true, opacity: 0.85 }));
      scene.add(sparks);
    }

    var statusEl = document.getElementById('movecount');

    function animate() {
      requestAnimationFrame(animate);
      var dt = Math.min(clock.getDelta(), 0.05);
      time += dt;
      var active = 0;
      queue.forEach(function (tw) {
        tw.t += dt;
        if (tw.t < 0 || tw.t > tw.dur + 0.4) return;
        active++;
        var k = Math.max(0, Math.min(1, tw.t / tw.dur));
        var e = 1 - Math.pow(1 - k, 3);
        tw.mesh.position.x = tw.from[0] + (tw.to[0] - tw.from[0]) * e;
        tw.mesh.position.z = tw.from[1] + (tw.to[1] - tw.from[1]) * e;
        tw.mesh.position.y = Math.sin(k * Math.PI) * 0.7;
        if (k >= 1) {
          tw.mesh.position.set(tw.to[0], 0, tw.to[1]);
          if (tw.promote) {  // corona: sustituye por la pieza real
            var parent = tw.mesh.parent, idx = parent.children.indexOf(tw.mesh);
            parent.remove(tw.mesh);
            var np = AICHESS_PIECES.makePiece(tw.promote, tw.color, style);
            np.position.set(tw.to[0], 0, tw.to[1]);
            np.traverse(function (o) { if (o.isMesh) o.castShadow = true; });
            parent.add(np);
            tw.mesh = np;
          }
        }
        if (tw.captured && k >= 1 && tw.fade < 1) {
          tw.fade = Math.min(1, tw.fade + dt * 3);
          tw.captured.traverse(function (o) {
            if (o.isMesh && o.material && o.material.transparent !== undefined) {
              o.material = o.material.clone(); o.material.transparent = true;
              o.material.opacity = 1 - tw.fade;
            }
          });
          if (tw.fade >= 1) scene.remove(tw.captured);
        }
      });
      if (statusEl) statusEl.textContent = active > 0 ? '▶ reproduciendo…' : '● posición final';
      if (pulse) pulse.material.opacity = 0.25 + 0.25 * Math.sin(time * 5);
      if (sparks) {
        var p = sparks.geometry.attributes.position.array;
        for (var i = 0; i < sparkVel.length; i++) {
          p[i * 3 + 1] += sparkVel[i] * dt;
          if (p[i * 3 + 1] > 4) p[i * 3 + 1] = 0;
        }
        sparks.geometry.attributes.position.needsUpdate = true;
        scene.traverse(function (o) {  // balanceo idle
          if (o.userData && o.userData.sq && o.userData.idle !== false) {
            o.rotation.z = Math.sin(time * 1.4 + o.position.x) * 0.02;
          }
        });
      }
      controls.update();
      renderer.render(scene, camera);
    }

    window.addEventListener('resize', function () {
      camera.aspect = mount.clientWidth / mount.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(mount.clientWidth, mount.clientHeight);
    });

    animate();
  }

  if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', init);
    } else { init(); }
  }

  // Exportado para tests Node (sin DOM).
  global.AICHESS_BOARD3D_TEST = {
    parseFenPlacement: parseFenPlacement, applyUci: applyUci, sq2xz: sq2xz
  };
})(typeof window !== 'undefined' ? window : this);
