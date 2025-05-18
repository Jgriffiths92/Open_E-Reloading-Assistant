import os

# Adjust this path if your architecture is different
gradle_path = ".buildozer/android/platform/build-arm64-v8a/dists/open_edope/app/build.gradle"

if not os.path.exists(gradle_path):
    print("Gradle file not found. Build your app once first.")
    exit(1)

with open(gradle_path, "r") as f:
    lines = f.readlines()

# Add plugin if not present
if "kotlin-android" not in "".join(lines):
    lines.insert(0, "apply plugin: 'kotlin-android'\n")

# Add dependency if not present
for i, line in enumerate(lines):
    if "dependencies {" in line:
        if 'implementation "org.jetbrains.kotlin:kotlin-stdlib' not in "".join(lines):
            lines.insert(i+1, '    implementation "org.jetbrains.kotlin:kotlin-stdlib:1.8.0"\n')
        break

with open(gradle_path, "w") as f:
    f.writelines(lines)

print("Gradle patched for Kotlin support.")