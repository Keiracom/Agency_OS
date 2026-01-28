"use client";

import { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";

interface NeonTunnelProps {
  className?: string;
  ringCount?: number;
  speed?: number;
}

function TunnelRing({
  position,
  rotation,
  color,
  scale = 1
}: {
  position: [number, number, number];
  rotation: number;
  color: string;
  scale?: number;
}) {
  return (
    <group position={position} rotation={[0, 0, rotation]} scale={scale}>
      <mesh>
        <torusGeometry args={[2, 0.02, 8, 64]} />
        <meshBasicMaterial color={color} transparent opacity={0.9} />
      </mesh>
      {/* Inner glow ring */}
      <mesh>
        <torusGeometry args={[2, 0.08, 8, 64]} />
        <meshBasicMaterial color={color} transparent opacity={0.2} />
      </mesh>
    </group>
  );
}

function Tunnel({ ringCount = 30, speed = 1 }: { ringCount?: number; speed?: number }) {
  const groupRef = useRef<THREE.Group>(null);
  const ringDataRef = useRef<{ z: number; rotation: number; color: string; scale: number }[]>([]);

  const colors = useMemo(() => ["#00d4ff", "#a855f7", "#ff00ff", "#00ffff", "#ff00aa"], []);

  // Initialize ring positions
  if (ringDataRef.current.length === 0) {
    for (let i = 0; i < ringCount; i++) {
      ringDataRef.current.push({
        z: -i * 2,
        rotation: (i * Math.PI) / 8,
        color: colors[i % colors.length],
        scale: 1 + (i * 0.05),
      });
    }
  }

  useFrame((state, delta) => {
    if (groupRef.current) {
      // Move rings toward camera
      ringDataRef.current.forEach((ring) => {
        ring.z += delta * speed * 3;
        ring.rotation += delta * 0.5;

        // Reset ring to back when it passes camera
        if (ring.z > 5) {
          ring.z = -(ringCount - 1) * 2;
          ring.scale = 1 + ((ringCount - 1) * 0.05);
        }
      });

      // Subtle camera sway
      groupRef.current.rotation.z = Math.sin(state.clock.elapsedTime * 0.2) * 0.05;
    }
  });

  return (
    <group ref={groupRef}>
      {ringDataRef.current.map((ring, index) => (
        <TunnelRing
          key={index}
          position={[0, 0, ring.z]}
          rotation={ring.rotation}
          color={ring.color}
          scale={ring.scale}
        />
      ))}
    </group>
  );
}

function CenterLight() {
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (meshRef.current) {
      const scale = 0.1 + Math.sin(state.clock.elapsedTime * 3) * 0.05;
      meshRef.current.scale.setScalar(scale);
    }
  });

  return (
    <mesh ref={meshRef} position={[0, 0, -50]}>
      <sphereGeometry args={[2, 16, 16]} />
      <meshBasicMaterial color="#ffffff" transparent opacity={0.8} />
    </mesh>
  );
}

function ParticleStreaks() {
  const pointsRef = useRef<THREE.Points>(null);

  const positions = useMemo(() => {
    const pos = new Float32Array(200 * 3);
    for (let i = 0; i < 200; i++) {
      const angle = Math.random() * Math.PI * 2;
      const radius = 1.5 + Math.random() * 1;
      pos[i * 3] = Math.cos(angle) * radius;
      pos[i * 3 + 1] = Math.sin(angle) * radius;
      pos[i * 3 + 2] = -Math.random() * 60;
    }
    return pos;
  }, []);

  useFrame((state, delta) => {
    if (pointsRef.current) {
      const positionAttribute = pointsRef.current.geometry.attributes.position;
      for (let i = 0; i < 200; i++) {
        let z = positionAttribute.getZ(i);
        z += delta * 10;
        if (z > 5) {
          z = -55;
        }
        positionAttribute.setZ(i, z);
      }
      positionAttribute.needsUpdate = true;
    }
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={200}
          array={positions}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.03}
        color="#00d4ff"
        transparent
        opacity={0.6}
        sizeAttenuation
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

export function NeonTunnel({ className = "", ringCount = 30, speed = 1 }: NeonTunnelProps) {
  return (
    <div className={`w-full h-full min-h-[300px] bg-slate-950 rounded-xl overflow-hidden ${className}`}>
      <Canvas
        camera={{ position: [0, 0, 3], fov: 75 }}
        gl={{ antialias: true, alpha: true }}
      >
        <color attach="background" args={["#050510"]} />
        <ambientLight intensity={0.1} />
        <Tunnel ringCount={ringCount} speed={speed} />
        <CenterLight />
        <ParticleStreaks />
        <fog attach="fog" args={["#050510", 1, 60]} />
      </Canvas>
    </div>
  );
}

export default NeonTunnel;
