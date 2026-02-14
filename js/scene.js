/* ============================================
   English Quest 3D - Three.js Scene
   ============================================ */

class Scene3D {
    constructor(canvas) {
        this.canvas = canvas;
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.particles = [];
        this.floatingObjects = [];
        this.clock = new THREE.Clock();
        this.mouse = { x: 0, y: 0 };
        this.targetCameraPos = { x: 0, y: 0 };
        this.currentTheme = 'menu';
        this.animationId = null;

        this.init();
    }

    init() {
        // Scene
        this.scene = new THREE.Scene();
        this.scene.fog = new THREE.FogExp2(0x0a0a1a, 0.015);

        // Camera
        this.camera = new THREE.PerspectiveCamera(
            60,
            window.innerWidth / window.innerHeight,
            0.1,
            1000
        );
        this.camera.position.set(0, 2, 15);

        // Renderer
        this.renderer = new THREE.WebGLRenderer({
            canvas: this.canvas,
            antialias: true,
            alpha: true
        });
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.renderer.toneMappingExposure = 1.2;

        // Lighting
        this.setupLights();

        // Create environment
        this.createStarField();
        this.createFloatingGeometry();
        this.createGround();
        this.createAurora();

        // Events
        window.addEventListener('resize', () => this.onResize());
        window.addEventListener('mousemove', (e) => this.onMouseMove(e));

        // Start animation
        this.animate();
    }

    setupLights() {
        // Ambient light
        const ambientLight = new THREE.AmbientLight(0x1a1a3e, 0.4);
        this.scene.add(ambientLight);

        // Main directional light
        const dirLight = new THREE.DirectionalLight(0x6c5ce7, 0.8);
        dirLight.position.set(5, 10, 5);
        dirLight.castShadow = true;
        dirLight.shadow.mapSize.width = 1024;
        dirLight.shadow.mapSize.height = 1024;
        this.scene.add(dirLight);

        // Accent lights
        const pointLight1 = new THREE.PointLight(0x00cec9, 1.5, 30);
        pointLight1.position.set(-8, 5, -5);
        this.scene.add(pointLight1);
        this.pointLight1 = pointLight1;

        const pointLight2 = new THREE.PointLight(0xfd79a8, 1.5, 30);
        pointLight2.position.set(8, 3, -3);
        this.scene.add(pointLight2);
        this.pointLight2 = pointLight2;

        const pointLight3 = new THREE.PointLight(0xfdcb6e, 1, 20);
        pointLight3.position.set(0, 8, 5);
        this.scene.add(pointLight3);
        this.pointLight3 = pointLight3;
    }

    createStarField() {
        const starsGeometry = new THREE.BufferGeometry();
        const starCount = 2000;
        const positions = new Float32Array(starCount * 3);
        const colors = new Float32Array(starCount * 3);
        const sizes = new Float32Array(starCount);

        for (let i = 0; i < starCount; i++) {
            const i3 = i * 3;
            const radius = 50 + Math.random() * 150;
            const theta = Math.random() * Math.PI * 2;
            const phi = Math.random() * Math.PI;

            positions[i3] = radius * Math.sin(phi) * Math.cos(theta);
            positions[i3 + 1] = radius * Math.sin(phi) * Math.sin(theta) - 20;
            positions[i3 + 2] = radius * Math.cos(phi);

            // Varied star colors
            const colorChoice = Math.random();
            if (colorChoice < 0.3) {
                colors[i3] = 0.42; colors[i3 + 1] = 0.36; colors[i3 + 2] = 0.91; // Purple
            } else if (colorChoice < 0.6) {
                colors[i3] = 0; colors[i3 + 1] = 0.81; colors[i3 + 2] = 0.79; // Teal
            } else {
                colors[i3] = 1; colors[i3 + 1] = 1; colors[i3 + 2] = 1; // White
            }

            sizes[i] = Math.random() * 2 + 0.5;
        }

        starsGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        starsGeometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
        starsGeometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));

        const starsMaterial = new THREE.PointsMaterial({
            size: 0.15,
            vertexColors: true,
            transparent: true,
            opacity: 0.8,
            sizeAttenuation: true
        });

        this.starField = new THREE.Points(starsGeometry, starsMaterial);
        this.scene.add(this.starField);
    }

    createFloatingGeometry() {
        const geometries = [
            new THREE.IcosahedronGeometry(0.5, 0),
            new THREE.OctahedronGeometry(0.5, 0),
            new THREE.TetrahedronGeometry(0.5, 0),
            new THREE.TorusGeometry(0.4, 0.15, 8, 16),
            new THREE.DodecahedronGeometry(0.4, 0),
            new THREE.TorusKnotGeometry(0.3, 0.1, 32, 8),
        ];

        const colors = [0x6c5ce7, 0x00cec9, 0xfd79a8, 0xfdcb6e, 0xa29bfe, 0x55efc4];

        for (let i = 0; i < 25; i++) {
            const geo = geometries[Math.floor(Math.random() * geometries.length)];
            const color = colors[Math.floor(Math.random() * colors.length)];

            const material = new THREE.MeshPhysicalMaterial({
                color: color,
                metalness: 0.3,
                roughness: 0.4,
                transparent: true,
                opacity: 0.7,
                emissive: color,
                emissiveIntensity: 0.15,
                wireframe: Math.random() > 0.5
            });

            const mesh = new THREE.Mesh(geo, material);

            // Position in a spread-out area
            mesh.position.set(
                (Math.random() - 0.5) * 40,
                (Math.random() - 0.5) * 20 + 3,
                (Math.random() - 0.5) * 30 - 10
            );

            mesh.rotation.set(
                Math.random() * Math.PI,
                Math.random() * Math.PI,
                Math.random() * Math.PI
            );

            const scale = 0.3 + Math.random() * 1.2;
            mesh.scale.set(scale, scale, scale);

            mesh.castShadow = true;

            this.scene.add(mesh);
            this.floatingObjects.push({
                mesh,
                rotSpeed: {
                    x: (Math.random() - 0.5) * 0.02,
                    y: (Math.random() - 0.5) * 0.02,
                    z: (Math.random() - 0.5) * 0.01
                },
                floatSpeed: 0.3 + Math.random() * 0.7,
                floatAmplitude: 0.3 + Math.random() * 0.8,
                initialY: mesh.position.y,
                phase: Math.random() * Math.PI * 2
            });
        }
    }

    createGround() {
        // Reflective ground plane
        const groundGeo = new THREE.PlaneGeometry(100, 100, 50, 50);
        const groundMat = new THREE.MeshPhysicalMaterial({
            color: 0x0a0a1a,
            metalness: 0.8,
            roughness: 0.2,
            transparent: true,
            opacity: 0.5,
            emissive: 0x1a1a3e,
            emissiveIntensity: 0.1
        });

        // Add wave displacement
        const positions = groundGeo.attributes.position;
        for (let i = 0; i < positions.count; i++) {
            const x = positions.getX(i);
            const z = positions.getZ(i);
            positions.setY(i, Math.sin(x * 0.3) * Math.cos(z * 0.3) * 0.3);
        }
        groundGeo.computeVertexNormals();

        const ground = new THREE.Mesh(groundGeo, groundMat);
        ground.rotation.x = -Math.PI / 2;
        ground.position.y = -5;
        ground.receiveShadow = true;
        this.scene.add(ground);
        this.ground = ground;
    }

    createAurora() {
        // Northern lights effect using a series of curved planes
        const auroraGroup = new THREE.Group();

        for (let a = 0; a < 3; a++) {
            const curve = new THREE.CatmullRomCurve3([
                new THREE.Vector3(-30, 15 + a * 3, -40),
                new THREE.Vector3(-10, 18 + a * 2, -35),
                new THREE.Vector3(5, 14 + a * 4, -38),
                new THREE.Vector3(20, 17 + a * 2, -36),
                new THREE.Vector3(35, 13 + a * 3, -40),
            ]);

            const tubeGeo = new THREE.TubeGeometry(curve, 64, 1.5 + a * 0.5, 8, false);
            const auroraMat = new THREE.MeshBasicMaterial({
                color: a === 0 ? 0x00cec9 : a === 1 ? 0x6c5ce7 : 0x55efc4,
                transparent: true,
                opacity: 0.08,
                side: THREE.DoubleSide,
                blending: THREE.AdditiveBlending
            });

            const auroraMesh = new THREE.Mesh(tubeGeo, auroraMat);
            auroraGroup.add(auroraMesh);
        }

        this.scene.add(auroraGroup);
        this.aurora = auroraGroup;
    }

    setTheme(theme) {
        this.currentTheme = theme;

        switch (theme) {
            case 'menu':
                this.targetCameraPos = { x: 0, y: 2, z: 15 };
                break;
            case 'game-match':
                this.targetCameraPos = { x: 0, y: 3, z: 12 };
                break;
            case 'game-spell':
                this.targetCameraPos = { x: -2, y: 2, z: 13 };
                break;
            case 'game-sentence':
                this.targetCameraPos = { x: 2, y: 3, z: 14 };
                break;
            case 'game-speed':
                this.targetCameraPos = { x: 0, y: 1, z: 10 };
                break;
            case 'results':
                this.targetCameraPos = { x: 0, y: 5, z: 18 };
                break;
        }
    }

    triggerCorrectEffect() {
        // Flash green lights
        if (this.pointLight1) {
            this.pointLight1.color.setHex(0x55efc4);
            this.pointLight1.intensity = 4;
            setTimeout(() => {
                this.pointLight1.color.setHex(0x00cec9);
                this.pointLight1.intensity = 1.5;
            }, 400);
        }
    }

    triggerWrongEffect() {
        // Flash red lights
        if (this.pointLight2) {
            this.pointLight2.color.setHex(0xff7675);
            this.pointLight2.intensity = 4;
            setTimeout(() => {
                this.pointLight2.color.setHex(0xfd79a8);
                this.pointLight2.intensity = 1.5;
            }, 400);
        }
    }

    triggerComboEffect() {
        // Pulse all lights
        [this.pointLight1, this.pointLight2, this.pointLight3].forEach(light => {
            if (light) {
                const origColor = light.color.getHex();
                const origIntensity = light.intensity;
                light.color.setHex(0xfdcb6e);
                light.intensity = 5;
                setTimeout(() => {
                    light.color.setHex(origColor);
                    light.intensity = origIntensity;
                }, 500);
            }
        });
    }

    onMouseMove(event) {
        this.mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
        this.mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
    }

    onResize() {
        this.camera.aspect = window.innerWidth / window.innerHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(window.innerWidth, window.innerHeight);
    }

    animate() {
        this.animationId = requestAnimationFrame(() => this.animate());

        const elapsed = this.clock.getElapsedTime();
        const delta = this.clock.getDelta();

        // Smooth camera movement following mouse
        const targetX = this.mouse.x * 1.5;
        const targetY = this.mouse.y * 0.8 + 2;
        this.camera.position.x += (targetX - this.camera.position.x) * 0.02;
        this.camera.position.y += (targetY - this.camera.position.y) * 0.02;
        this.camera.lookAt(0, 1, 0);

        // Rotate star field slowly
        if (this.starField) {
            this.starField.rotation.y += 0.0002;
            this.starField.rotation.x += 0.0001;
        }

        // Animate floating objects
        this.floatingObjects.forEach(obj => {
            obj.mesh.rotation.x += obj.rotSpeed.x;
            obj.mesh.rotation.y += obj.rotSpeed.y;
            obj.mesh.rotation.z += obj.rotSpeed.z;

            obj.mesh.position.y = obj.initialY +
                Math.sin(elapsed * obj.floatSpeed + obj.phase) * obj.floatAmplitude;
        });

        // Animate aurora
        if (this.aurora) {
            this.aurora.rotation.y = Math.sin(elapsed * 0.1) * 0.05;
            this.aurora.children.forEach((child, i) => {
                child.material.opacity = 0.06 + Math.sin(elapsed * 0.5 + i) * 0.03;
            });
        }

        // Animate ground
        if (this.ground) {
            const positions = this.ground.geometry.attributes.position;
            for (let i = 0; i < positions.count; i++) {
                const x = positions.getX(i);
                const z = positions.getZ(i);
                positions.setY(i,
                    Math.sin(x * 0.3 + elapsed * 0.5) *
                    Math.cos(z * 0.3 + elapsed * 0.3) * 0.3
                );
            }
            positions.needsUpdate = true;
            this.ground.geometry.computeVertexNormals();
        }

        // Animate point lights
        if (this.pointLight1) {
            this.pointLight1.position.x = -8 + Math.sin(elapsed * 0.5) * 3;
            this.pointLight1.position.z = -5 + Math.cos(elapsed * 0.3) * 2;
        }
        if (this.pointLight2) {
            this.pointLight2.position.x = 8 + Math.cos(elapsed * 0.4) * 3;
            this.pointLight2.position.z = -3 + Math.sin(elapsed * 0.6) * 2;
        }

        this.renderer.render(this.scene, this.camera);
    }

    dispose() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
    }
}
