# Amplifying Difference: A Perceptual and Cognitive Analysis of the Entviz Algorithm for Human-Centric Entropy Visualization

## Daniel Hardman

## [`daniel.hardman@gmail.com`](mailto:daniel.hardman@gmail.com)

## September 2025

# 1\. Introduction

## 1.1. The Human Bottleneck in Cryptographic Verification

In contemporary digital ecosystems, the burden of security is increasingly shifting towards the end-user. From verifying public key fingerprints for secure shell (SSH) connections to confirming the validity of blockchain payment addresses, non-expert users are frequently placed in the critical path of security-sensitive verification tasks.1 These tasks often hinge on the comparison of high-entropy data—long, seemingly random strings of alphanumeric characters. However, a significant body of research in usable security has demonstrated that this reliance on manual string comparison represents a fundamental human bottleneck.2

The challenge is not merely that humans are "bad" at this task; rather, the task itself is profoundly misaligned with the architecture of human cognition. Comparing strings like fc94b0c1e5b0987c and fc94b0c1e5b0987d forces the brain into a serial, character-by-character cognitive mode that is slow, cognitively demanding, and highly susceptible to error.2 This presents a system design failure, not a user failure. It demands a cognitive modality for which the human brain is ill-equipped, while ignoring one of its greatest strengths: the rapid, parallel, and holistic processing of visual patterns.5 The consequences of this misalignment are severe, potentially leading to man-in-the-middle (MitM) attacks, financial loss, and a general erosion of trust in secure systems.

## 1.2. Hash Visualization as a Human-Centric Solution

To address this critical gap, the field of "Hash Visualization" emerged, pioneered by the seminal work of Perrig and Song in 1999\.2 The core premise of this approach is to transform the verification task by converting abstract, meaningless data into structured, perceptible images. This technique seeks to replace a well-documented human processing weakness (serial string comparison) with a proven human strength (holistic pattern recognition).5 By mapping cryptographic hashes to visual fingerprints, these systems aim to make differences between two distinct data chunks not just detectable, but immediately and intuitively obvious to a human observer. This represents a fundamental shift in the cognitive modality of the verification task itself, moving from slow, analytical processing to rapid, perceptual judgment.

## 1.3. Introducing Entviz: A Multi-Channel Approach

This paper presents a comprehensive analysis of entviz, a novel algorithm for visualizing high-entropy data.11 The stated goal of entviz is to "allow an untrained adult with reasonably good vision to easily decide whether two chunks of entropy are the same or different".11 Entviz distinguishes itself from earlier approaches through a systematic, multi-channel design that is explicitly engineered to align with the principles of human perception and cognition. It losslessly represents all bits of entropy across three distinct but complementary visual channels:

1. A primary textual channel, tokenized into a grid for easy reading and spot-checking.

2. A secondary channel of edge shapes and colors, designed to form larger, emergent patterns.

3. A tertiary channel of nucleus background colors, serving as a redundant hint.

Furthermore, entviz introduces a novel concept of "visual CRCs"—deterministically placed blank cells and quartile marks that act as salient landmarks to surface differences that might otherwise be hidden.11 This evolution from the stochastic, artistic generation of early systems like Random Art to the deliberate, perceptually-engineered output of entviz signifies a maturation of the field. Where the first generation of hash visualization proved the concept's viability, entviz aims to optimize it by designing its visual output based on the known constraints and capabilities of the human perceptual system.

## 1.4. Thesis and Paper Structure

The central thesis of this paper is that entviz represents a significant advancement in human-centric hash visualization by systematically applying principles from cognitive psychology and psychophysics to amplify difference. This design philosophy contrasts sharply with machine-optimized representations like QR codes and constitutes a principled improvement upon earlier human-centric attempts like SSH randomart.

To substantiate this thesis, this report is structured as follows. Section 2 establishes the theoretical foundation, reviewing the cognitive architecture of human pattern recognition and the psychophysical principles of visual distinguishability. Section 3 articulates the fundamental conceptual dichotomy between visual hashes designed for machine-based similarity detection and those designed for human-centric difference amplification. Section 4 provides a detailed comparative analysis of three distinct approaches: SSH randomart, QR codes, and entviz, evaluating each against the established perceptual and cognitive framework. Section 5 synthesizes these findings to propose a set of evidence-based design principles for future human-centric visual hashing systems. Finally, Section 6 concludes with a summary of contributions and a discussion of their broader implications for the field of usable security.

# 2\. The Perceptual and Cognitive Framework for Visual Comparison

To properly evaluate any system designed for human visual verification, one must first understand the underlying mechanisms of human perception and cognition. This section establishes a theoretical framework grounded in two key disciplines: cognitive psychology, which explains how we organize and remember patterns, and psychophysics, which quantifies the limits of our ability to distinguish between visual stimuli.

## 2.1. The Cognitive Architecture of Pattern Recognition

The human ability to recognize patterns is not a monolithic skill but an emergent property of multiple interlocking cognitive systems that are hardwired to extract order from sensory data.12 This faculty is foundational to learning, navigation, and social interaction.13

### 2.1.1. Gestalt Principles of Perceptual Organization

In the early 20th century, Gestalt psychologists proposed that the brain creates a perception—a gestalt, or unified whole—that is more than the sum of its sensory inputs.15 This organization is not random but follows a set of predictable principles that describe how we instinctively group visual elements to reduce complexity and form coherent structures.15 Key principles relevant to the design of visual hashes include:

* Figure-Ground: We instinctively segment our visual world into a figure (the object of focus) and a ground (the background).15 This separation is essential for identifying salient patterns in noisy environments.12

* Proximity: Elements that are close to one another are perceived as a single group.15 This allows us to recognize clusters and boundaries within data without explicit borders.

* Similarity: Objects that share visual characteristics such as shape, color, or size are perceived as being part of the same pattern.15 This helps in discerning repeating elements and establishing relationships.

* Continuity (or Good Continuation): The eye tends to follow the smoothest path, perceiving continuous lines and patterns rather than disjointed or jagged ones.16 This aids in tracking flow and maintaining coherence.

* Closure: Our brains automatically fill in missing information to perceive incomplete patterns as complete wholes.16 This powerful principle allows for the creation of recognizable forms from minimal information.

These principles demonstrate that human perception is not a passive reception of data but an active process of construction.12 Our minds are predisposed to impose order, complete incomplete information, and compress complex visual scenes into manageable mental representations.

### 2.1.2. Memorability and Distinguishability

The ease with which a pattern is perceived is intrinsically linked to its memorability. A growing body of research has shown that images possess an intrinsic memorability that is consistent across observers and tasks.18 Highly memorable images are perceived more readily, potentially because they better match stored neural templates or schemas used for recognition.20 Studies have consistently shown that humans prefer, and are better at processing, ordered and symmetrical patterns over random, unstructured ones.21 This preference for regularity is a key factor in both the distinguishability and memorability of abstract visual patterns. The ability to recognize familiar faces, for example, relies on rapidly identifying unique patterns in facial features and their spatial relationships.13 A good visual hash should aim to create patterns that are similarly distinctive and easy to encode into memory.

### 2.1.3. The Cognitive Load of Visual Noise and Clutter

A fundamental tension exists between the information density of a visual representation and the cognitive capacity of the human observer. The Gestalt principles function as cognitive compression mechanisms, allowing us to simplify complex scenes. However, when a visual stimulus is dense, random, and lacks the structure that these principles rely on, it becomes cognitively incompressible. This is the nature of visual noise.

Processing such patterns imposes a significant cognitive load, as the brain must resort to a high-effort, element-by-element analysis rather than holistic recognition.22 This cognitive overload is exacerbated by the phenomenon of "crowding," where the presence of clutter fundamentally limits our ability to recognize an object, even if it is clearly visible.25 Studies have shown that dynamic visual noise can directly interfere with the retention of information in visual short-term memory.26 Therefore, a core principle for any human-centric design must be to minimize visual noise and maximize Gestalt coherence, thereby reducing the cognitive load required for the comparison task.

## 2.2. The Psychophysics of Distinguishability: Just Noticeable Difference (JND)

While cognitive psychology explains *how* we perceive patterns, psychophysics provides the tools to quantify *what* we can perceive. A visual hash algorithm that aims to make differences "obvious" must generate visual changes that exceed the perceptual thresholds of its users. The concept of the Just Noticeable Difference (JND) provides a formal framework for this, acting as a critical design specification. Designing a visual hash without considering JND thresholds is akin to designing an audio alert without considering the limits of human hearing; it risks creating "differences" that are imperceptible in practice.

### 2.2.1. Weber's Law and the Difference Threshold

The JND, also known as the difference threshold, is defined as the minimum change in a stimulus that can be detected by an observer at least 50% of the time.28 In the 19th century, Ernst Weber discovered a fundamental relationship, now known as Weber's Law, which states that the JND is a constant proportion of the original stimulus intensity.28 This is expressed mathematically as:  
IΔ/I​=k  
where I is the original stimulus intensity, ΔI is the JND, and k is the constant Weber fraction. This law holds true for many, though not all, sensory dimensions and implies that our ability to detect change is relative, not absolute. We are better at detecting a 1 kg difference when comparing 2 kg and 3 kg weights than when comparing 20 kg and 21 kg weights.

### 2.2.2. JND Thresholds for Visual Primitives

For a visual hash algorithm like entviz, which relies on primitives of shape, size, and color, understanding the JNDs for these specific features is paramount. The following table summarizes key findings from psychophysical research.

| Visual Feature | JND Threshold (Weber Fraction or other metric) | Conditions/Notes | Source Citation(s) |
| :---- | :---- | :---- | :---- |
| **Size (Length)** | Weber fractions range from 0.025 to 0.036 for humans. | Performance degrades as object size approaches spatial resolution limits. | 34 |
| **Size (Area/Volume)** | Weber fractions average 0.13-0.16. | Thresholds are influenced by object shape (tetrahedrons are harder to discriminate) and size (smaller objects are harder). | 35 |
| **Shape (Aspect Ratio)** | As low as 1.6% (0.016) for squares/circles. | Threshold increases progressively as the shape becomes more elongated. Discrimination is superior to size discrimination. | 34 |
| **Shape (Curvature)** | Weber fractions average 0.11-0.14. | Performance varies with the radius of curvature; smaller radii may be easier to discriminate via direct touch. | 36 |
| **Angle** | Complex dual-peak fluctuation (not a constant fraction). | JND is lowest near 90° and 180°, and highest near 45° and 135°. Perception is based on an internal orthogonal reference frame. | 38 |
| **Color (Luminance)** | Follows Weber's Law, with a Weber fraction of approximately 0.08. | The human eye is less sensitive to luminance changes in very dark or very bright areas. | 30 |
| **Color (Chromaticity \- Normal Vision)** | Represented by MacAdam ellipses on the CIE chromaticity diagram. | A ΔE value of 1 is considered the JND threshold. Sensitivity varies with hue and saturation (e.g., lower for highly saturated colors). | 40 |
| **Color (Chromaticity \- CVD)** | Significantly larger thresholds. ΔE values of 15-22 units for mild deficiency, up to 50-60 for severe deficiency. | Specific color confusions depend on the type of Color Vision Deficiency (e.g., protanopia, deuteranopia). | 42 |

Table 2: Summary of Just Noticeable Difference (JND) Thresholds for Key Visual Features. 

This table collates disparate, highly technical data from psychophysics research into a single, accessible reference, providing the empirical backbone for a quantitative analysis of the design choices in visual hash algorithms.

### 2.2.3. Considerations for Ordinary Vision

The design of a visual hash must account for the range of visual capabilities in the general population, not just for an idealized observer with perfect vision. A common benchmark for functional vision is 20/40 acuity, which means an individual can see an object at 20 feet with the same clarity that a person with 20/20 vision sees at 40 feet.44 This implies a lower resolution for perceiving fine details. Therefore, visual elements intended to be distinguishable must be sufficiently large and clear to remain above the JND threshold even for users with less-than-perfect acuity. Similarly, the high prevalence of color vision deficiency (CVD) necessitates the use of color palettes whose differences are large enough in color space to be discriminable by common forms of CVD.42

# 3\. A Tale of Two Philosophies: Visual Hashes for Machines vs. Humans

The term "visual hash" is dangerously ambiguous, as it is used to describe two classes of algorithms with diametrically opposed goals. This ambiguity can lead to profound design errors if an algorithm from one class is misapplied to a problem requiring the other. A crucial contribution of this analysis is to establish a clear taxonomy: "Perceptual Hashing" for machine-based similarity detection and "Authentication Visualization" for human-centric distinguishability.

## 3.1. Perceptual Hashing for Machine Similarity

Perceptual hashing algorithms are designed to solve the problem of near-duplicate detection for multimedia content.46 Their design philosophy is rooted in the concept of robustness.

* Core Principle: Robustness and Similarity: The primary objective is to generate a compact fingerprint of a file such that two files that are perceptually similar will have hashes that are also similar (i.e., have a small distance between them).47 The algorithm is explicitly designed to be resilient to content-preserving manipulations such as JPEG compression, resizing, watermarking, or minor adjustments to brightness and contrast.48 In essence, these algorithms are a form of lossy compression that preserves the semantic "content" of an image while discarding superficial details.

* Mechanism: Noise Reduction and Feature Abstraction: Perceptual hashing functions as a process of noise reduction. It treats transformations like compression artifacts or changes in file format as "noise" that obscures the core "signal" of the image's content. The algorithm's purpose is to filter out this noise. This is typically achieved by transforming the image into a canonical form (e.g., resizing to a small, fixed size like 8×8 pixels, converting to grayscale) and then abstracting its most salient features, such as its average color or its low-frequency components via a Discrete Cosine Transform (DCT).48 The resulting hash is a compact representation of these robust features. Similarity is then computed using a distance metric, like the Hamming distance, which counts the number of differing bits between two hashes.46

* Application: The canonical use cases are in digital forensics for identifying known child sexual abuse material (CSAM), copyright enforcement on platforms like YouTube, and large-scale content-based image retrieval.46 In all these scenarios, the system needs to answer the question: "Are these two images fundamentally the same, despite minor modifications?"

## 3.2. Hash Visualization for Human Distinguishability

In stark contrast, hash visualization algorithms for human verification are designed around the principle of sensitivity. Their purpose is not to find similarity but to make even the slightest difference impossible to ignore.

* Core Principle: Amplifying Difference (Visual Avalanche Effect): The fundamental goal is to create a visual representation where a minimal change in the input data—even a single bit flip—produces a dramatic and immediately obvious change in the resulting image.51 This is the conceptual opposite of a perceptual hash. It seeks to create a "visual avalanche effect" that mirrors the avalanche effect of the underlying cryptographic hash function, where small input changes lead to drastic output changes.49

* Mechanism: Signal Amplification and Perceptual Salience: This approach functions as a process of signal amplification. Every bit of the input cryptographic hash is treated as critical signal, with no concept of "noise." The algorithm's job is to translate any change in this signal into a visual alarm that is well above the Just Noticeable Difference (JND) threshold of the human perceptual system. As first proposed by Perrig and Song, this requires the algorithm to generate structured, regular images that leverage human pattern recognition strengths and satisfy properties like "near collision resistance"—making it computationally infeasible to find two distinct inputs that produce perceptually similar images.2

* Application: The primary use cases are in security-critical human-in-the-loop verification tasks, such as validating a server's public key fingerprint during an SSH connection or confirming a cryptocurrency address before a transaction.1 The system is designed to help a human confidently answer the question: "Are these two cryptographic keys exactly the same?" Using a machine-centric perceptual hash for this task would be a catastrophic failure, as an attacker could craft a malicious key that is computationally different but produces a visually identical or nearly identical image, deceiving the user.

# 4\. A Comparative Analysis of Visual Entropy Representations

To understand the practical implications of these differing design philosophies, this section provides a comparative analysis of three distinct systems: SSH randomart, an early attempt at human-centric visualization; QR codes, a purely machine-centric paradigm; and entviz, a modern system designed explicitly with human cognition in mind.

## 4.1. SSH Randomart: A Random Walk in a Constrained Space

The "randomart" image generated by OpenSSH is one of the most widely deployed examples of hash visualization. It was developed to make the process of verifying a server's public key fingerprint easier and more intuitive than comparing hexadecimal strings.52

* Algorithm and Goal: The algorithm, colloquially known as the "drunken bishop," performs a diagonal random walk across a constrained 17×9 character grid.53 The server's key fingerprint (a hash) is broken into 2-bit chunks, with each chunk dictating the bishop's next move (up-left, up-right, down-left, or down-right). The final image is an ASCII representation of the path, where each character corresponds to the number of times the bishop visited that position.53 The goal is to create a unique picture from the key, which a user might recall from previous connections.53

* Cognitive Analysis: From a perceptual standpoint, randomart occupies a middle ground. The images it produces are more structured than pure random noise, often featuring a central cluster with radiating lines due to the nature of the random walk.54 However, they generally lack strong, coherent Gestalt features. The patterns are emergent rather than designed, composed of a single primitive (a path segment) arranged randomly. User studies confirm that observers attempt to impose their own structure, looking for "general cues like the placement of the dots or big letters like B or S or E".55 This indicates that users are actively searching for Gestalt figures within the randomness, a cognitively demanding task.

* Performance and Limitations: Empirical studies have yielded a mixed assessment of randomart's effectiveness.

  * Security and Accuracy: In one user study, it performed moderately well, with 10% of participants failing to detect a simulated MitM attack, a better rate than for hexadecimal strings (21%) but worse than for sentences (6%).55 Another study concluded that it enabled "fast and accurate comparisons" for both easy and hard-to-distinguish pairs, with 98% and 94% accuracy, respectively.56

  * Usability: It is relatively fast for users to compare, with a median time of around 5.5 seconds.55 However, it has two significant usability drawbacks: it is computationally expensive to generate, making it suboptimal for low-power devices, and its abstract nature makes it very difficult for users to describe verbally to another person for verification.56

  * Perceptual Entropy: Randomart's most critical flaw is its low perceptual entropy. A detailed analysis estimated that, despite being generated from a 128-bit or 160-bit hash, the resulting image contains only between 19.71 and 23.71 bits of information that is perceivable by a human.56 This low entropy makes it theoretically vulnerable to brute-force attacks where an adversary could generate a malicious key whose randomart image is perceptually identical to a target's.

## 4.2. QR Codes: A Paradigm of Machine-Centric Design

Quick Response (QR) codes are a ubiquitous form of 2D matrix barcode. Their design is a masterclass in engineering for machine readability, prioritizing data density, scanning speed, and error correction above all else.58

* Algorithm and Goal: A QR code encodes data into a grid of black and white modules. Its structure is optimized for machine vision, featuring three large finder patterns at the corners for orientation, smaller alignment patterns, and timing patterns.60 It incorporates a quiet zone to isolate the code from its surroundings and uses robust Reed-Solomon error correction, which allows it to be read even if a portion of the code is damaged or obscured.60

* Cognitive Analysis: QR codes are the antithesis of human-centric design. They present a dense field of high-frequency visual noise that actively violates nearly every Gestalt principle. There is no proximity-based grouping of meaningful elements, no similarity to follow, no continuous lines, and no closure to complete. The pattern is intentionally random and complex to maximize data capacity.21 Consequently, the cognitive load required for a human to even attempt a visual comparison of two QR codes is immense.22 Studies on visual complexity show that such patterns can overwhelm users, and the lack of recognizable structure makes them impossible to memorize or compare holistically.24

* Performance and Limitations (for Human Comparison): While exceptionally effective for their intended purpose—machine scanning—QR codes are completely unsuitable for human verification. Their inclusion in this analysis serves as a critical baseline, illustrating the design outcomes when human perceptual and cognitive factors are not a consideration. They represent a local maximum for machine efficiency and a global minimum for human usability in the context of visual comparison.

## 4.3. Entviz: A Multi-Channel, Human-Cognition-Aware Design

Entviz is a modern algorithm that explicitly aims to bridge the gap between the information-theoretic requirements of representing entropy and the perceptual-cognitive requirements of human verification.11 Its design can be deconstructed and mapped directly onto the cognitive and psychophysical framework established in Section 2\.

* Algorithm and Goal: The entviz algorithm normalizes an input entropy string, divides it into 3-byte (24-bit) tokens, and arranges these tokens in a grid.11 The entropy within each token is then used to control multiple visual channels: the text content of the cell, the shape and color of the cell's six edges, and the background color of the cell's nucleus. Additionally, global properties of the entropy are used to place salient landmarks like blank cells and quartile marks.11 The stated goal is unambiguous: easy visual comparison for an untrained adult.11

* Cognitive Analysis:

  * Grid and Tokenization (Proximity and Reduced Load): By breaking a long, monolithic string into a grid of 4-character tokens, entviz immediately leverages the Gestalt principle of Proximity. This chunking reduces the cognitive load of comparison, allowing for both holistic scanning and targeted spot-checking of individual cells—a stated design requirement.11

  * Edge Shapes (Gestalt Coherence): The algorithm uses a palette of eight distinct geometric primitives (triangle, hook, rect, box, slant, hammer, pyramid, double bars) for the cell edges.11 Unlike the single primitive of randomart, this richer set of shapes is more likely to trigger Gestalt grouping. Adjacent shapes can connect to form larger, emergent patterns, engaging the principles of  
    Continuity and Closure.11 This creates structured, memorable compositions rather than random textures. The careful selection of these shapes, with varying angles, curvatures, and aspect ratios, can be evaluated against JND thresholds to ensure their perceptual distinguishability.34

  * Color Palette (JND and Accessibility): Entviz uses a limited, high-contrast 5-color palette (\[white, gold, red, blue, black\]) and explicitly states the requirement of being usable by people with common forms of color blindness.11 This is a direct application of psychophysical principles. The chosen colors must have a color difference (ΔE) large enough to exceed the JND thresholds not only for normal vision but also for color-deficient vision, ensuring the Similarity grouping principle remains effective for all users.41

  * Visual CRCs (Salient Landmarks): The deterministic placement of blank cells and quartile marks is a groundbreaking innovation in visual hash design. Cognitively, these features act as highly salient landmarks that break the pattern's regularity, immediately capturing attention and leveraging the Figure-Ground principle. This transforms the verification task. Instead of requiring a comprehensive, high-load comparison of the entire pattern, a user can employ a much more efficient, heuristic-based check: "Are the blank cells in the same place?" A negative answer terminates the comparison instantly. This provides an explicit design affordance for the "spot-checking" that users attempt to perform implicitly and less reliably with other systems.11

  * Multi-Channel Redundancy: By encoding the same entropy across text, edge shape/color, and nucleus color, entviz builds in robustness.11 A difference that is subtle in one channel (e.g., a slight change in nucleus color) may be obvious in another (e.g., the text changes from cxJ3 to cxJ4). This redundancy provides multiple pathways for difference detection, increasing the overall reliability of the human-in-the-loop verification process.

The following table provides a synthesis of this comparative analysis, contrasting the design philosophies and key attributes of the different systems.

| Dimension | Perceptual Hashing (for Machines) | SSH Randomart | QR Codes | Entviz |
| :---- | :---- | :---- | :---- | :---- |
| **Primary Goal** | Similarity Detection | Distinguishability | Data Storage & Retrieval | Difference Amplification |
| **Target User** | Automated Systems / Machine Vision | Human (Security-Aware) | Machine Vision | Human (Untrained Adult) |
| **Core Mechanism** | Feature Abstraction & Noise Reduction | Random Walk Path Generation | Dense Matrix Encoding | Multi-Channel Feature Mapping |
| **Information Density** | Low (Hash Fingerprint) | Low | Very High | High (Lossless) |
| **Cognitive Load** | N/A | Moderate | Extremely High | Low |
| **Key Gestalt Principle(s) Leveraged** | N/A | Emergence (of weak patterns) | None | Proximity, Similarity, Continuity, Closure, Figure-Ground |
| **Key Gestalt Principle(s) Violated** | N/A | (Weakly adheres to most) | All | None |
| **Estimated Perceptual Entropy** | N/A | Low (\~20-24 bits) 56 | N/A (Intractable for humans) | High (Theoretically all bits are represented in perceptible channels) |

*Table 1: Comparison of Visual Hashing Philosophies and Implementations.*

# 5\. Synthesis and A Framework for Human-Centric Visual Hashing

## 5.1. Synthesizing the Analysis

The comparative analysis reveals a clear trajectory in the design of visual entropy representations. QR codes demonstrate the efficacy of a purely machine-centric approach, achieving high data density at the cost of complete human illegibility. SSH randomart represents a pioneering but naive step towards human-centric design; it successfully replaces a string with an image but relies on the emergent, often weak, patterns of a random process, resulting in low perceptual entropy and ambiguous features.

Entviz, in contrast, represents a more mature and principled approach. Its design demonstrates a systematic application of the cognitive and psychophysical principles outlined in Section 2\. It actively avoids the cognitive pitfalls of visual noise inherent in QR codes and directly addresses the structural and perceptual shortcomings of randomart. The superiority of the entviz design lies not in any single feature but in its underlying philosophy: it is an act of perceptual engineering. Rather than generating an image and hoping it is human-parsable, it starts with the constraints of the human visual system and builds a visual language to fit them. The use of a structured grid, a rich set of geometric primitives, a perceptually validated color palette, and the novel concept of "visual CRCs" collectively create a system that is designed to work with human cognition, not against it.

## 5.2. Proposed Design Principles for Human-Centric Visual Hashes

Based on this analysis, a framework of evidence-based design principles can be proposed for the development of future human-centric authentication visualizations.

* Principle 1: Maximize Gestalt Coherence, Minimize Visual Noise. Visualizations should be constructed from simple, regular, and easily nameable geometric primitives. These primitives should be arranged in a structured manner (e.g., a grid) that encourages the natural Gestalt grouping effects of Proximity, Similarity, Continuity, and Closure. High-frequency, random, or chaotic patterns that create visual noise and increase cognitive load should be explicitly avoided.

* Principle 2: Design Above Perceptual Thresholds (JND). The visual features used to encode bits of entropy—such as differences in shape, size, angle, or color—must be separated by a magnitude significantly greater than the established Just Noticeable Difference (JND) for that feature. This design must explicitly account for the target user population, including robust performance for individuals with common visual impairments like reduced acuity (e.g., 20/40 vision) and color vision deficiency.

* Principle 3: Incorporate Salient Landmarks (Visual CRCs). The design should include a small number of easily identifiable and verifiable features that are derived from the global properties of the entropy. These landmarks, such as entviz's blank cells or quartile marks, provide powerful cognitive shortcuts for rapid, low-effort rejection of non-matching hashes, transforming the task from an exhaustive comparison to an efficient heuristic check.

* Principle 4: Employ Multi-Channel Redundancy. To enhance robustness against individual perceptual differences or momentary lapses in attention, the same entropy should be encoded through multiple, complementary visual channels. This could include combinations of text, graphics, shape, color, and position. If a difference is missed in one channel, it can still be caught in another.

## 5.3. Avenues for Future Research

While the theoretical analysis of entviz is promising, its practical efficacy must be validated through empirical user studies. The most critical next step is to conduct rigorous, controlled experiments that measure user performance (in terms of accuracy and speed) and subjective cognitive workload when comparing entviz images versus SSH randomart images. These studies should mirror the methodologies of prior work, subjecting participants to simulated man-in-the-middle attacks under realistic conditions of time pressure and habituation.55 Such research would provide quantitative evidence to support or refute the hypothesized benefits of entviz's design. Further research could also involve psychophysical experiments to optimize the specific shape and color palettes used in entviz, ensuring maximal distinguishability across the widest possible range of users and viewing conditions.

# 6\. Conclusion

## 6.1. Summary of Contributions

This paper has sought to provide a rigorous, human-centric analysis of the entviz algorithm. Its primary contributions are threefold. First, it has established a comprehensive framework for evaluating such systems, drawing upon foundational principles from cognitive psychology (Gestalt theory, pattern recognition, cognitive load) and psychophysics (Just Noticeable Difference). Second, it has articulated and clarified the fundamental philosophical dichotomy between machine-centric perceptual hashing, which prioritizes robustness to similarity, and human-centric authentication visualization, which must prioritize sensitivity to difference. Third, through a detailed comparative analysis, it has positioned entviz as a state-of-the-art implementation of this human-centric philosophy, demonstrating how its multi-channel, landmark-based design is a principled and significant improvement over previous approaches.

## 6.2. Broader Implications

The challenges addressed by systems like entviz are not niche academic concerns. As cryptographic tools become more deeply embedded in the fabric of daily life—from secure messaging to digital finance—the need for effective human-in-the-loop verification will only grow. The historical approach of presenting users with raw cryptographic data and expecting them to perform flawlessly has proven to be a persistent source of systemic weakness. The work embodied by entviz suggests a more promising path forward: one that respects the limitations and leverages the profound strengths of the human perceptual system. By designing security interfaces that are cognitively ergonomic, we can build systems that are not only more secure in theory but are also more trustworthy and usable in practice. The principles of perceptual engineering are not merely an aesthetic enhancement for security but a critical requirement for its successful deployment in the real world.

# Works cited

1. Human Distinguishable Visual Key Fingerprints \- USENIX, accessed September 4, 2025, [https://www.usenix.org/system/files/sec20-azimpourkivi.pdf](https://www.usenix.org/system/files/sec20-azimpourkivi.pdf)  
2. Hash Visualization: a New Technique to improve Real-World Security, accessed September 4, 2025, [https://netsec.ethz.ch/publications/papers/validation.pdf](https://netsec.ethz.ch/publications/papers/validation.pdf)  
3. Hash Visualization: a New Technique to improve Real-World Security \- CiteSeerX, accessed September 4, 2025, [https://citeseerx.ist.psu.edu/document?repid=rep1\&type=pdf\&doi=c62b2636b6d90e5e7cefda14fc565f25cc2a465b](https://citeseerx.ist.psu.edu/document?repid=rep1&type=pdf&doi=c62b2636b6d90e5e7cefda14fc565f25cc2a465b)  
4. Hash Visualization: a New Technique to improve Real-World Security \- Semantic Scholar, accessed September 4, 2025, [https://www.semanticscholar.org/paper/Hash-Visualization%3A-a-New-Technique-to-improve-Perrig-Song/57e58e630ed2b8ca2029aa970b862aa59d53a3dc](https://www.semanticscholar.org/paper/Hash-Visualization%3A-a-New-Technique-to-improve-Perrig-Song/57e58e630ed2b8ca2029aa970b862aa59d53a3dc)  
5. Using hash visualization for real-time user ... \- GI Digital Library, accessed September 4, 2025, [https://dl.gi.de/bitstreams/0fcdb871-29a6-40c6-b000-5f667fd50d17/download](https://dl.gi.de/bitstreams/0fcdb871-29a6-40c6-b000-5f667fd50d17/download)  
6. Using hash visualization for real-time user-governed password validation \- ResearchGate, accessed September 4, 2025, [https://www.researchgate.net/publication/334561177\_Using\_hash\_visualization\_for\_real-time\_user-governed\_password\_validation](https://www.researchgate.net/publication/334561177_Using_hash_visualization_for_real-time_user-governed_password_validation)  
7. Using hash visualization for real-time user-governed password validation \- Science, accessed September 4, 2025, [https://fietkau.science/hash\_visualization\_password\_validation](https://fietkau.science/hash_visualization_password_validation)  
8. Hash Visualization: a New Technique to improve Real-World Security \- People @EECS, accessed September 4, 2025, [https://people.eecs.berkeley.edu/\~dawnsong/papers/randomart.pdf](https://people.eecs.berkeley.edu/~dawnsong/papers/randomart.pdf)  
9. A Graphical PIN Authentication Mechanism for Smart Cards ... \- UNISA, accessed September 4, 2025, [http://www.di-srv.unisa.it/\~luicat/publications/prise07.pdf](http://www.di-srv.unisa.it/~luicat/publications/prise07.pdf)  
10. A graphical PIN authentication mechanism with ... \- SciSpace, accessed September 4, 2025, [https://scispace.com/pdf/a-graphical-pin-authentication-mechanism-with-applications-2pk9yf1x06.pdf](https://scispace.com/pdf/a-graphical-pin-authentication-mechanism-with-applications-2pk9yf1x06.pdf)  
11. entviz-readme.pdf  
12. The Cognitive Architecture of Pattern Recognition: A Psychological and Computational Lens, accessed September 4, 2025, [https://mgclaybrook.com/blog/the-cognitive-architecture-of-pattern-recognition-a-psychological-and-computational-lens/o5niua](https://mgclaybrook.com/blog/the-cognitive-architecture-of-pattern-recognition-a-psychological-and-computational-lens/o5niua)  
13. A Cognitive Psychology Blog » Never Doubt The Power of Patterns \- Web – A Colby, accessed September 4, 2025, [https://web.colby.edu/cogblog/2020/11/30/never-doubt-the-power-of-patterns/](https://web.colby.edu/cogblog/2020/11/30/never-doubt-the-power-of-patterns/)  
14. Exploring Cognitive Skills: Pattern Recognition \- HappyNeuron Pro, accessed September 4, 2025, [https://www.happyneuronpro.com/en/info/what-is-pattern-recognition/](https://www.happyneuronpro.com/en/info/what-is-pattern-recognition/)  
15. Gestalt Principles of Perception | Introduction to Psychology, accessed September 4, 2025, [https://courses.lumenlearning.com/waymaker-psychology/chapter/gestalt-principles-of-perception/](https://courses.lumenlearning.com/waymaker-psychology/chapter/gestalt-principles-of-perception/)  
16. Gestalt psychology \- Wikipedia, accessed September 4, 2025, [https://en.wikipedia.org/wiki/Gestalt\_psychology](https://en.wikipedia.org/wiki/Gestalt_psychology)  
17. Gestalt Principles \- The Decision Lab, accessed September 4, 2025, [https://thedecisionlab.com/reference-guide/psychology/gestalt-principles](https://thedecisionlab.com/reference-guide/psychology/gestalt-principles)  
18. PsyArXiv Preprints | Memorability: Reconceptualizing Memory as a Visual Attribute \- OSF, accessed September 4, 2025, [https://osf.io/preprints/psyarxiv/ckv92/](https://osf.io/preprints/psyarxiv/ckv92/)  
19. Perceptual encoding benefit of visual memorability on visual memory formation \- PMC \- PubMed Central, accessed September 4, 2025, [https://pmc.ncbi.nlm.nih.gov/articles/PMC11369960/](https://pmc.ncbi.nlm.nih.gov/articles/PMC11369960/)  
20. Highly memorable images are more readily perceived \- PubMed, accessed September 4, 2025, [https://pubmed.ncbi.nlm.nih.gov/38695797/](https://pubmed.ncbi.nlm.nih.gov/38695797/)  
21. (PDF) Production and perception rules underlying visual patterns: Effects of symmetry and hierarchy \- ResearchGate, accessed September 4, 2025, [https://www.researchgate.net/publication/225296501\_Production\_and\_perception\_rules\_underlying\_visual\_patterns\_Effects\_of\_symmetry\_and\_hierarchy](https://www.researchgate.net/publication/225296501_Production_and_perception_rules_underlying_visual_patterns_Effects_of_symmetry_and_hierarchy)  
22. A Neurophysiological Evaluation of Cognitive Load during Augmented Reality Interactions in Various Industrial Maintenance and Assembly Tasks \- MDPI, accessed September 4, 2025, [https://www.mdpi.com/resolver?pii=s23187698](https://www.mdpi.com/resolver?pii=s23187698)  
23. Decoding Auditory Feedback: Enhancing Usability of RFID and QR code scanning methods with Sound Insights \- UU Research Portal, accessed September 4, 2025, [https://research-portal.uu.nl/ws/portalfiles/portal/242790976/3673805.3673822.pdf](https://research-portal.uu.nl/ws/portalfiles/portal/242790976/3673805.3673822.pdf)  
24. The curious versus the overwhelmed: Factors influencing QR codes scan intention \- King's Research Portal, accessed September 4, 2025, [https://kclpure.kcl.ac.uk/portal/files/78511596/JBR\_author\_accepted\_version.pdf](https://kclpure.kcl.ac.uk/portal/files/78511596/JBR_author_accepted_version.pdf)  
25. Visual Crowding: a fundamental limit on conscious perception and object recognition \- PMC, accessed September 4, 2025, [https://pmc.ncbi.nlm.nih.gov/articles/PMC3070834/](https://pmc.ncbi.nlm.nih.gov/articles/PMC3070834/)  
26. Dynamic visual noise affects visual short-term memory for surface color, but not spatial location \- PubMed, accessed September 4, 2025, [https://pubmed.ncbi.nlm.nih.gov/20178960/](https://pubmed.ncbi.nlm.nih.gov/20178960/)  
27. Short-Term Memory Recall of Visual Patterns Under Static and Dynamic Visual Noise, accessed September 4, 2025, [https://www.researchgate.net/publication/299999657\_Short-term\_memory\_recall\_of\_visual\_patterns\_under\_static\_and\_dynamic\_visual\_noise](https://www.researchgate.net/publication/299999657_Short-term_memory_recall_of_visual_patterns_under_static_and_dynamic_visual_noise)  
28. Just-Noticeable Difference | Biology for Majors II \- Lumen Learning, accessed September 4, 2025, [https://courses.lumenlearning.com/wm-biology2/chapter/just-noticeable-difference/](https://courses.lumenlearning.com/wm-biology2/chapter/just-noticeable-difference/)  
29. Just Noticeable Difference (JND) in Psychology \- Verywell Mind, accessed September 4, 2025, [https://www.verywellmind.com/what-is-the-just-noticeable-difference-2795306](https://www.verywellmind.com/what-is-the-just-noticeable-difference-2795306)  
30. Just-noticeable difference \- Wikipedia, accessed September 4, 2025, [https://en.wikipedia.org/wiki/Just-noticeable\_difference](https://en.wikipedia.org/wiki/Just-noticeable_difference)  
31. Just Noticeable Difference (JND) in Psychology: Examples & Definition, accessed September 4, 2025, [https://www.simplypsychology.org/what-is-the-just-noticeable-difference.html](https://www.simplypsychology.org/what-is-the-just-noticeable-difference.html)  
32. Grasping follows Weber's law: How to use response variability as a proxy for JND \- PMC, accessed September 4, 2025, [https://pmc.ncbi.nlm.nih.gov/articles/PMC9669808/](https://pmc.ncbi.nlm.nih.gov/articles/PMC9669808/)  
33. Weber's law and thresholds (video) \- Khan Academy, accessed September 4, 2025, [https://www.khanacademy.org/test-prep/mcat/processing-the-environment/sensory-perception/v/webers-law-and-thresholds](https://www.khanacademy.org/test-prep/mcat/processing-the-environment/sensory-perception/v/webers-law-and-thresholds)  
34. Shape and size discrimination compared \- ResearchGate, accessed September 4, 2025, [https://www.researchgate.net/publication/49696872\_Shape\_and\_size\_discrimination\_compared](https://www.researchgate.net/publication/49696872_Shape_and_size_discrimination_compared)  
35. Discrimination thresholds for haptic perception of volume, surface ..., accessed September 4, 2025, [https://pmc.ncbi.nlm.nih.gov/articles/PMC3222810/](https://pmc.ncbi.nlm.nih.gov/articles/PMC3222810/)  
36. Perception of Curvature and Object Motion Via Contact Location Feedback \- ResearchGate, accessed September 4, 2025, [https://www.researchgate.net/publication/225174107\_Perception\_of\_Curvature\_and\_Object\_Motion\_Via\_Contact\_Location\_Feedback](https://www.researchgate.net/publication/225174107_Perception_of_Curvature_and_Object_Motion_Via_Contact_Location_Feedback)  
37. Perceptual Analysis of Level-of-Detail: The JND Approach \- Computer Science, accessed September 4, 2025, [https://www.cs.dartmouth.edu/\~xingdong/papers/ISM06.pdf](https://www.cs.dartmouth.edu/~xingdong/papers/ISM06.pdf)  
38. The human visual system estimates angle features in an internal ..., accessed September 4, 2025, [https://jov.arvojournals.org/article.aspx?articleid=2718450](https://jov.arvojournals.org/article.aspx?articleid=2718450)  
39. Just Noticeable Differences (JNDs) | JND \- Society for Imaging Informatics in Medicine, accessed September 4, 2025, [https://siim.org/otpedia/just-noticeable-differences-jnds-jnd/](https://siim.org/otpedia/just-noticeable-differences-jnds-jnd/)  
40. A Just Noticeable Difference: Measuring JND for Displays | Radiant ..., accessed September 4, 2025, [https://www.radiantvisionsystems.com/blog/just-noticeable-difference-measuring-jnd-displays](https://www.radiantvisionsystems.com/blog/just-noticeable-difference-measuring-jnd-displays)  
41. Color discrimination threshold of the human eye \- Part V \- Precise Color Communication, accessed September 4, 2025, [https://www.konicaminolta.com/instruments/knowledge/color/part5/02.html](https://www.konicaminolta.com/instruments/knowledge/color/part5/02.html)  
42. Assessing Color Discrimination \- Scholarly Commons, accessed September 4, 2025, [https://commons.erau.edu/cgi/viewcontent.cgi?article=1102\&context=edt](https://commons.erau.edu/cgi/viewcontent.cgi?article=1102&context=edt)  
43. Color-discrimination threshold determination using pseudoisochromatic test plates, accessed September 4, 2025, [https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2014.01376/full](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2014.01376/full)  
44. Evaluation of Visual Acuity \- StatPearls \- NCBI Bookshelf, accessed September 4, 2025, [https://www.ncbi.nlm.nih.gov/books/NBK564307/](https://www.ncbi.nlm.nih.gov/books/NBK564307/)  
45. Types of Color Vision Deficiency | National Eye Institute, accessed September 4, 2025, [https://www.nei.nih.gov/learn-about-eye-health/eye-conditions-and-diseases/color-blindness/types-color-vision-deficiency](https://www.nei.nih.gov/learn-about-eye-health/eye-conditions-and-diseases/color-blindness/types-color-vision-deficiency)  
46. PHVSpec: A Benchmark-based Analysis of Perceptual Hash Systems for Videos \- Tech Coalition, accessed September 4, 2025, [https://technologycoalition.org/wp-content/uploads/Tech-Coalition-Video-Hash-Benchmark-Paper.pdf](https://technologycoalition.org/wp-content/uploads/Tech-Coalition-Video-Hash-Benchmark-Paper.pdf)  
47. It's Not What It Looks Like: Manipulating Perceptual Hashing based Applications \- Gang Wang, accessed September 4, 2025, [https://gangw.cs.illinois.edu/PHashing.pdf](https://gangw.cs.illinois.edu/PHashing.pdf)  
48. Overview of Perceptual Hashing Technology \- Ofcom, accessed September 4, 2025, [https://www.ofcom.org.uk/siteassets/resources/documents/research-and-data/online-research/other/perceptual-hashing-technology.pdf?v=328806](https://www.ofcom.org.uk/siteassets/resources/documents/research-and-data/online-research/other/perceptual-hashing-technology.pdf?v=328806)  
49. pHash.org: Home of pHash, the open source perceptual hash library, accessed September 4, 2025, [https://www.phash.org/](https://www.phash.org/)  
50. A Visual Model-Based Perceptual Image Hash for Content Authentication \- ResearchGate, accessed September 4, 2025, [https://www.researchgate.net/publication/276428507\_A\_Visual\_Model-Based\_Perceptual\_Image\_Hash\_for\_Content\_Authentication](https://www.researchgate.net/publication/276428507_A_Visual_Model-Based_Perceptual_Image_Hash_for_Content_Authentication)  
51. The Drunken Bishop Algorithm \- Hacker News, accessed September 4, 2025, [https://news.ycombinator.com/item?id=28070831](https://news.ycombinator.com/item?id=28070831)  
52. kelvinkoon/DrunkenBishop: Visual fingerprint algorithm implementation \- GitHub, accessed September 4, 2025, [https://github.com/kelvinkoon/DrunkenBishop](https://github.com/kelvinkoon/DrunkenBishop)  
53. The drunken bishop: An analysis of the OpenSSH ... \- Dirk Loss, accessed September 4, 2025, [http://dirk-loss.de/sshvis/drunken\_bishop.pdf](http://dirk-loss.de/sshvis/drunken_bishop.pdf)  
54. Making art with SSH key randomart \- Benjojo's Blog, accessed September 4, 2025, [https://blog.benjojo.co.uk/post/ssh-randomart-how-does-it-work-art](https://blog.benjojo.co.uk/post/ssh-randomart-how-does-it-work-art)  
55. Can Unicorns Help Users Compare Crypto Key ... \- Joshua Tan, accessed September 4, 2025, [https://joshktan.com/papers/chi17.pdf](https://joshktan.com/papers/chi17.pdf)  
56. A Study of User-Friendly Hash Comparison Schemes \- Network ..., accessed September 4, 2025, [https://netsec.ethz.ch/publications/papers/visual\_hash\_acsac09.pdf](https://netsec.ethz.ch/publications/papers/visual_hash_acsac09.pdf)  
57. Human and AI Perceptual Differences in Image Classification Errors \- arXiv, accessed September 4, 2025, [https://arxiv.org/html/2304.08733v2](https://arxiv.org/html/2304.08733v2)  
58. QR code \- Wikipedia, accessed September 4, 2025, [https://en.wikipedia.org/wiki/QR\_code](https://en.wikipedia.org/wiki/QR_code)  
59. Accessibility and QR codes \- TetraLogical, accessed September 4, 2025, [https://tetralogical.com/blog/2022/08/08/accessibility-and-qr-codes/](https://tetralogical.com/blog/2022/08/08/accessibility-and-qr-codes/)  
60. A DETAILED ANALYSIS OF QR CODE AND A TECHNIQUE TO GENERATE QR CODES FOR CRYTOGRAPHY \- iaset.us, accessed September 4, 2025, [http://www.iaset.us/index.php/download/archives/--1381471393-2.%20Comp%20Sci%20-%20IJCSE%20-%20A%20DETAILED%20ANALYSIS%20OF%20QR%20CODE%20AND%20-%20Tanmay%20Sawant.pdf](http://www.iaset.us/index.php/download/archives/--1381471393-2.%20Comp%20Sci%20-%20IJCSE%20-%20A%20DETAILED%20ANALYSIS%20OF%20QR%20CODE%20AND%20-%20Tanmay%20Sawant.pdf)  
61. Best practices for QR code legibility: Improve readability, accessed September 4, 2025, [https://qrcodekit.com/guides/best-practices-for-qr-code-legibility/](https://qrcodekit.com/guides/best-practices-for-qr-code-legibility/)  
62. Best Practices for QR Code Readability \- Pageloot, accessed September 4, 2025, [https://pageloot.com/blog/best-practices-for-qr-code-readability/](https://pageloot.com/blog/best-practices-for-qr-code-readability/)  
63. QR Code Printing Guidelines – The Definitive Guide 2025 \- Uniqode, accessed September 4, 2025, [https://www.uniqode.com/blog/qr-code-best-practices/qr-code-printing-guideline](https://www.uniqode.com/blog/qr-code-best-practices/qr-code-printing-guideline)  
64. Human Cognitive Benchmarks Reveal Foundational Visual Gaps in MLLMs \- arXiv, accessed September 4, 2025, [https://arxiv.org/html/2502.16435v2](https://arxiv.org/html/2502.16435v2)  
65. The Curious Versus the Overwhelmed: Factors Influencing QR Codes Scan Intention, accessed September 4, 2025, [https://www.researchgate.net/publication/319964542\_The\_Curious\_Versus\_the\_Overwhelmed\_Factors\_Influencing\_QR\_Codes\_Scan\_Intention](https://www.researchgate.net/publication/319964542_The_Curious_Versus_the_Overwhelmed_Factors_Influencing_QR_Codes_Scan_Intention)  
66. Factors influencing QR codes scan intention, accessed September 4, 2025, [https://e-tarjome.com/storage/panel/fileuploads/2019-07-20/1563607852\_E12233-e-tarjome.pdf](https://e-tarjome.com/storage/panel/fileuploads/2019-07-20/1563607852_E12233-e-tarjome.pdf)