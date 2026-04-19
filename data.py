"""
data.py — PhysicsMentor AI
Defines and loads the ChromaDB knowledge base.

12 documents (exceeds minimum of 10), each covering ONE specific topic,
100-500 words each, designed to answer concrete student questions.

Design decision: Documents are written at 'intermediate' level so the
difficulty_adapter_node can simplify or expand them when generating answers.
Each document includes physical intuition, not just formulas.
"""

from sentence_transformers import SentenceTransformer
import chromadb

KB_DOCUMENTS = [
    {
        "id": "doc_001",
        "topic": "Newton's Laws of Motion",
        "text": (
            "Newton's three laws of motion are the foundation of classical mechanics. "
            "The First Law (Law of Inertia) states that an object remains at rest or in "
            "uniform motion unless acted upon by a net external force. This is why passengers "
            "lurch forward when a bus brakes suddenly — their bodies want to keep moving. "
            "The Second Law (Law of Acceleration) quantifies how forces change motion: "
            "F = ma, where F is the net force in Newtons, m is mass in kilograms, and a is "
            "acceleration in m/s². This means doubling the force on the same object doubles "
            "its acceleration. Doubling the mass while keeping force constant halves the "
            "acceleration. The Third Law states that for every action there is an equal and "
            "opposite reaction. When you push a wall, the wall pushes back on you with the "
            "same magnitude. This is why rockets work: hot gases are expelled downward "
            "(action) and the rocket accelerates upward (reaction). A common misconception "
            "is that action-reaction forces cancel each other out — they don't, because they "
            "act on different objects. Net force on an object is zero only when all forces "
            "on THAT object cancel."
        )
    },
    {
        "id": "doc_002",
        "topic": "Work, Energy and Power",
        "text": (
            "Work is done when a force displaces an object in the direction of the force. "
            "W = F × d × cos(θ), where θ is the angle between force and displacement. "
            "If you carry a heavy bag horizontally, you do zero work against gravity because "
            "your vertical force and horizontal displacement are perpendicular (cos 90° = 0). "
            "Kinetic energy (KE) is the energy of motion: KE = ½mv². The ½ factor comes from "
            "integrating F = ma over displacement using the work-energy theorem. Without it, "
            "the formula gives twice the actual energy — a common student error. "
            "Potential energy (PE) is stored energy due to position: PE = mgh for gravitational "
            "PE near Earth's surface. The work-energy theorem states that net work done on an "
            "object equals its change in kinetic energy: W_net = ΔKE. "
            "Power is the rate of doing work: P = W/t = F × v. A 100W bulb consumes 100 joules "
            "per second. The unit of energy, the Joule, equals 1 kg·m²/s². "
            "Energy conservation: in a closed system with no friction, total mechanical energy "
            "(KE + PE) remains constant. As a ball falls, PE decreases and KE increases by the "
            "same amount."
        )
    },
    {
        "id": "doc_003",
        "topic": "Laws of Thermodynamics",
        "text": (
            "Thermodynamics studies heat, temperature, and energy transformation. "
            "The Zeroth Law states that if two systems are each in thermal equilibrium with "
            "a third, they are in equilibrium with each other. This justifies the concept of "
            "temperature as a universal measure. "
            "The First Law is energy conservation for thermodynamic systems: "
            "ΔU = Q - W, where ΔU is change in internal energy, Q is heat added to the system, "
            "and W is work done BY the system. If you compress a gas (do work ON it), its "
            "internal energy rises and it heats up. "
            "The Second Law introduces entropy: heat naturally flows from hot to cold, never "
            "spontaneously in reverse. No heat engine can be 100% efficient — some energy is "
            "always lost to the cold reservoir. The efficiency of a Carnot engine (ideal maximum) "
            "is η = 1 - T_cold/T_hot, where temperatures are in Kelvin. "
            "The Third Law states that as temperature approaches absolute zero (0 K = -273.15°C), "
            "entropy approaches a minimum constant value. You cannot reach absolute zero in a "
            "finite number of steps. "
            "Entropy is often described as disorder, but more precisely it measures the number "
            "of microscopic configurations that produce the same macroscopic state."
        )
    },
    {
        "id": "doc_004",
        "topic": "Electric Current and Ohm's Law",
        "text": (
            "Electric current is the rate of flow of electric charge: I = Q/t, measured in "
            "Amperes (A). One ampere means one coulomb of charge passing a cross-section per second. "
            "Current flows from high potential (positive terminal) to low potential (negative terminal) "
            "in conventional notation — electrons actually move in the opposite direction. "
            "Ohm's Law relates voltage, current, and resistance: V = IR. Voltage (V) is the "
            "potential difference driving the current, resistance (R) is the opposition to flow "
            "(measured in Ohms, Ω). A common error is writing I = VR — the correct rearrangement "
            "is I = V/R. "
            "Resistances in series add directly: R_total = R1 + R2 + R3. "
            "Resistances in parallel add as reciprocals: 1/R_total = 1/R1 + 1/R2. "
            "Parallel combination always gives a LOWER resistance than any single resistor in the group. "
            "Power dissipated in a resistor: P = IV = I²R = V²/R. "
            "Kirchhoff's Current Law: the sum of currents entering a node equals the sum leaving. "
            "Kirchhoff's Voltage Law: the sum of voltage drops around any closed loop equals zero."
        )
    },
    {
        "id": "doc_005",
        "topic": "Capacitors and Capacitance",
        "text": (
            "A capacitor stores electric charge and energy in an electric field between two "
            "conducting plates separated by an insulating material (dielectric). "
            "Capacitance C = Q/V, measured in Farads (F). One Farad is enormous — practical "
            "capacitors are in microfarads (μF) or picofarads (pF). "
            "For a parallel-plate capacitor: C = ε₀εᵣA/d, where A is plate area, d is separation, "
            "ε₀ = 8.85 × 10⁻¹² F/m (permittivity of free space), and εᵣ is the relative permittivity "
            "of the dielectric. Increasing plate area or decreasing separation increases capacitance. "
            "Energy stored in a capacitor: U = ½CV² = Q²/(2C). The ½ factor appears because charging "
            "a capacitor requires progressively more work as charge builds up — average voltage during "
            "charging is half the final voltage. "
            "Capacitors in series: 1/C_total = 1/C1 + 1/C2 (like parallel resistors — the opposite!). "
            "Capacitors in parallel: C_total = C1 + C2 (like series resistors). "
            "In DC circuits, a fully charged capacitor blocks current. In AC circuits, capacitors "
            "allow alternating current to pass — their impedance is Xc = 1/(2πfC)."
        )
    },
    {
        "id": "doc_006",
        "topic": "Magnetic Force and Faraday's Law",
        "text": (
            "A magnetic field exerts force on moving charges and current-carrying conductors. "
            "The magnetic force on a charge: F = qvB sinθ, where q is charge, v is velocity, "
            "B is magnetic field strength (in Tesla), and θ is the angle between v and B. "
            "When θ = 90°, force is maximum. When θ = 0° (charge moves parallel to B), force is zero. "
            "The direction of force is given by the right-hand rule (or left-hand for negative charges). "
            "Force on a current-carrying wire: F = BIL sinθ, where I is current and L is wire length. "
            "Faraday's Law of electromagnetic induction: a changing magnetic flux through a loop "
            "induces an electromotive force (EMF): ε = -dΦ/dt, where Φ = BA cosθ is magnetic flux. "
            "The negative sign (Lenz's Law) means the induced current opposes the change causing it. "
            "Move a magnet into a coil — current flows to create a magnetic field opposing the entry. "
            "This is the principle behind electric generators: rotating a coil in a magnetic field "
            "continuously changes the flux, inducing alternating current. "
            "The unit of magnetic field is Tesla (T): 1 T = 1 kg/(A·s²)."
        )
    },
    {
        "id": "doc_007",
        "topic": "Wave Motion and Sound",
        "text": (
            "A wave transfers energy through a medium without transferring matter. "
            "Transverse waves: oscillation perpendicular to wave travel (light, water surface waves). "
            "Longitudinal waves: oscillation parallel to wave travel (sound, seismic P-waves). "
            "Key wave parameters: wavelength (λ) — distance between two consecutive crests; "
            "frequency (f) — oscillations per second (Hz); period (T = 1/f) — time per oscillation; "
            "amplitude — maximum displacement from equilibrium. "
            "Wave speed: v = fλ. A common error is writing v = f/λ or v = λ/f — remember, "
            "higher frequency means more wave cycles per second, so at the same speed, wavelength "
            "must be shorter: fλ = constant for a given medium. "
            "Sound is a longitudinal mechanical wave requiring a medium — it cannot travel through vacuum. "
            "Speed of sound in air at 20°C ≈ 343 m/s. "
            "The Doppler effect: when a source moves toward you, you perceive a higher frequency "
            "(pitch); when it moves away, lower frequency. This is why a siren sounds higher as an "
            "ambulance approaches and drops as it passes."
        )
    },
    {
        "id": "doc_008",
        "topic": "Optics — Reflection and Refraction",
        "text": (
            "Reflection: when light hits a surface, the angle of incidence equals the angle of "
            "reflection (measured from the normal to the surface). Regular (specular) reflection "
            "occurs on smooth surfaces; diffuse reflection on rough surfaces. "
            "Refraction: when light passes from one medium to another, it bends because its speed "
            "changes. Snell's Law: n₁ sin θ₁ = n₂ sin θ₂, where n is the refractive index "
            "(n = c/v, where c = 3 × 10⁸ m/s is the speed of light in vacuum). "
            "Light bends toward the normal when entering a denser medium (higher n) and away from "
            "the normal when entering a less dense medium. "
            "Total Internal Reflection (TIR) occurs when light in a dense medium hits the boundary "
            "at an angle greater than the critical angle: sin θc = n₂/n₁. "
            "Fiber optic cables use TIR to keep light trapped inside the glass core. "
            "Lenses use refraction to converge or diverge light. "
            "Convex (converging) lens: focal length positive, used in cameras and eyes. "
            "Concave (diverging) lens: focal length negative, used in glasses for nearsightedness. "
            "Lens formula: 1/v - 1/u = 1/f (with appropriate sign conventions)."
        )
    },
    {
        "id": "doc_009",
        "topic": "Modern Physics and Photoelectric Effect",
        "text": (
            "Modern physics departs from classical mechanics when dealing with very high speeds "
            "(relativity) or very small scales (quantum mechanics). "
            "The photoelectric effect: when light of sufficient frequency hits a metal surface, "
            "electrons are ejected. Key observations: (1) electrons are emitted only if frequency "
            "exceeds a threshold f₀, regardless of intensity; (2) above threshold, increasing "
            "intensity increases current (more electrons), not their energy; (3) increasing frequency "
            "increases the maximum kinetic energy of ejected electrons. "
            "Einstein explained this by proposing light consists of photons, each with energy "
            "E = hf, where h = 6.626 × 10⁻³⁴ J·s is Planck's constant. "
            "A photon must overcome the work function φ (binding energy of the electron to the metal): "
            "KE_max = hf - φ. If hf < φ, no electrons are emitted. "
            "de Broglie's hypothesis: matter has wave properties. The de Broglie wavelength: "
            "λ = h/mv, where m is mass and v is velocity. This explains electron diffraction. "
            "Special relativity (Einstein): E = mc². The rest energy of mass m is mc², where "
            "c = 3 × 10⁸ m/s. This is why nuclear reactions release enormous energy from tiny "
            "mass changes."
        )
    },
    {
        "id": "doc_010",
        "topic": "Circular Motion and Gravitation",
        "text": (
            "Circular motion requires a centripetal force directed toward the center of the circle. "
            "This is not a new type of force — it is the NET force resulting from existing forces "
            "(gravity, tension, normal force, friction) that happens to point inward. "
            "Centripetal acceleration: a_c = v²/r = ω²r, where ω = 2πf is angular velocity. "
            "Centripetal force: F_c = mv²/r. "
            "A common misconception: there is no 'centrifugal force' pushing you outward on a merry-go-round. "
            "What you feel is your inertia resisting the inward centripetal force. "
            "Newton's Law of Universal Gravitation: F = Gm₁m₂/r², where G = 6.674 × 10⁻¹¹ N·m²/kg² "
            "is the gravitational constant. Gravity obeys an inverse-square law — double the distance "
            "and gravity becomes ¼ as strong. "
            "For a satellite in circular orbit: gravitational force provides centripetal force: "
            "Gm₁m₂/r² = mv²/r, giving orbital speed v = √(GM/r). "
            "Escape velocity: the minimum speed to escape a planet's gravity: v_escape = √(2GM/r). "
            "The geostationary orbit is at ~35,786 km above Earth's equator, where orbital period = 24 hours."
        )
    },
    {
        "id": "doc_011",
        "topic": "Simple Harmonic Motion",
        "text": (
            "Simple Harmonic Motion (SHM) is oscillatory motion where the restoring force is "
            "proportional to and opposite in direction to the displacement: F = -kx. "
            "Examples: mass on a spring, simple pendulum (for small angles). "
            "For a mass-spring system: angular frequency ω = √(k/m), period T = 2π√(m/k). "
            "A heavier mass oscillates more slowly (higher T). A stiffer spring oscillates faster. "
            "Displacement in SHM: x(t) = A cos(ωt + φ), where A is amplitude and φ is phase. "
            "Velocity: v(t) = -Aω sin(ωt + φ). Maximum velocity at x = 0 (equilibrium). "
            "Acceleration: a(t) = -Aω² cos(ωt + φ) = -ω²x. "
            "Energy in SHM: total energy E = ½kA² remains constant. At maximum displacement, "
            "all energy is potential (½kA²) and KE = 0. At equilibrium, all energy is kinetic. "
            "Simple pendulum period: T = 2π√(L/g), valid only for small angles (< 15°). "
            "Importantly, period does NOT depend on amplitude (for small angles) or mass — "
            "only on length and gravity. This is why pendulum clocks are reliable."
        )
    },
    {
        "id": "doc_012",
        "topic": "Fluid Mechanics and Bernoulli's Principle",
        "text": (
            "Fluid mechanics studies liquids and gases at rest (hydrostatics) and in motion (fluid dynamics). "
            "Pressure at depth h in a fluid: P = P₀ + ρgh, where P₀ is surface pressure, ρ is density, "
            "g = 9.8 m/s², h is depth. Pressure increases linearly with depth — this is why deep-sea "
            "vehicles need thick hulls. "
            "Archimedes' Principle: a submerged object experiences an upward buoyant force equal to the "
            "weight of fluid it displaces: F_buoy = ρ_fluid × g × V_displaced. An object floats if its "
            "average density is less than the fluid's density. "
            "Equation of Continuity (for incompressible fluids): A₁v₁ = A₂v₂. Where a pipe narrows, "
            "fluid must speed up. This is why water from a garden hose speeds up when you partially "
            "cover the opening. "
            "Bernoulli's Principle: along a streamline, P + ½ρv² + ρgh = constant. Where fluid flows "
            "faster, pressure is lower. This explains airplane lift: air flows faster over the curved "
            "upper wing, creating lower pressure above than below, resulting in net upward force. "
            "Viscosity is a fluid's internal resistance to flow — honey has high viscosity, water low. "
            "Reynolds number Re = ρvL/μ distinguishes laminar (smooth, Re < 2300) from turbulent flow."
        )
    },
]


def build_knowledge_base():
    """
    Initialize ChromaDB in-memory collection and populate with KB documents.
    Returns (collection, embedder) for use by retrieval_node.
    """
    print("Initialising knowledge base — loading sentence transformer...")
    embedder = SentenceTransformer('all-MiniLM-L6-v2')

    client = chromadb.Client()  # in-memory

    # Create or get collection
    collection = client.get_or_create_collection(
        name="physics_mentor_kb",
        metadata={"hnsw:space": "cosine"}
    )

    # Add documents if collection is empty
    if collection.count() == 0:
        print(f"Populating knowledge base with {len(KB_DOCUMENTS)} documents...")
        texts = [doc["text"] for doc in KB_DOCUMENTS]
        ids = [doc["id"] for doc in KB_DOCUMENTS]
        metadatas = [{"topic": doc["topic"]} for doc in KB_DOCUMENTS]
        embeddings = embedder.encode(texts).tolist()

        collection.add(
            documents=texts,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas
        )
        print(f"Knowledge base ready: {collection.count()} documents loaded.")
    else:
        print(f"Knowledge base already populated: {collection.count()} documents.")

    return collection, embedder
