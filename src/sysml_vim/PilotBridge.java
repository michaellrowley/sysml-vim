package org.sysmlvim.bridge;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.InputStreamReader;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import org.eclipse.emf.common.util.TreeIterator;
import org.eclipse.emf.common.util.URI;
import org.eclipse.emf.ecore.EAttribute;
import org.eclipse.emf.ecore.EObject;
import org.eclipse.emf.ecore.EReference;
import org.eclipse.emf.ecore.EStructuralFeature;
import org.eclipse.emf.ecore.resource.Resource;
import org.eclipse.xtext.nodemodel.INode;
import org.eclipse.xtext.nodemodel.util.NodeModelUtils;
import org.eclipse.xtext.resource.IResourceServiceProvider;
import org.eclipse.xtext.resource.XtextResource;
import org.eclipse.xtext.util.CancelIndicator;
import org.eclipse.xtext.validation.CheckMode;
import org.eclipse.xtext.validation.Issue;
import org.eclipse.xtext.validation.IResourceValidator;
import org.omg.sysml.interactive.SysMLInteractive;

/** JSON bridge to the official Pilot's Xtext parser and validator. */
public final class PilotBridge {
    private static final Gson JSON = new GsonBuilder().disableHtmlEscaping().create();
    private static final String PILOT_NAME = "SysML v2 Pilot Implementation";
    private static final List<String> SUPPORTED_STANDARDS = List.of("SysML 2.0", "KerML 1.0");

    private PilotBridge() {}

    public static void main(String[] arguments) {
        int exitCode = run(arguments);
        if (exitCode != 0) {
            System.exit(exitCode);
        }
    }

    private static int run(String[] arguments) {
        boolean rpcMode = arguments.length == 0;
        JsonElement requestId = null;
        try {
            if (!rpcMode && (arguments.length != 2 || !"parse".equals(arguments[0]))) {
                throw new IllegalArgumentException("usage: run.py parse <workspace>");
            }
            JsonObject request;
            try (InputStreamReader input = new InputStreamReader(System.in, StandardCharsets.UTF_8)) {
                request = JsonParser.parseReader(input).getAsJsonObject();
            }
            if (rpcMode) {
                requestId = request.get("id");
                if (!"2.0".equals(stringValue(request.get("jsonrpc")))) {
                    throw new IllegalArgumentException("JSON-RPC version must be 2.0");
                }
                if (!"parse".equals(stringValue(request.get("method")))) {
                    writeRpcError(requestId, -32601, "unknown parser method");
                    return 0;
                }
                JsonObject parameters = request.getAsJsonObject("params");
                if (parameters == null || stringValue(parameters.get("path")) == null) {
                    throw new IllegalArgumentException("parse requests require params.path");
                }
                request = parameters;
            }

            JsonObject parseResult;
            ByteArrayOutputStream pilotConsoleOutput = new ByteArrayOutputStream();
            PrintStream protocolOutput = System.out;
            try (PrintStream capturedPilotOutput =
                    new PrintStream(pilotConsoleOutput, true, StandardCharsets.UTF_8)) {
                System.setOut(capturedPilotOutput);
                try {
                    parseResult = parseWorkspace(request);
                } finally {
                    System.setOut(protocolOutput);
                }
            }
            if (pilotConsoleOutput.size() > 0) {
                byte[] consoleBytes = pilotConsoleOutput.toByteArray();
                System.err.write(consoleBytes, 0, consoleBytes.length);
            }
            if (rpcMode) {
                JsonObject rpcResponse = new JsonObject();
                rpcResponse.addProperty("jsonrpc", "2.0");
                rpcResponse.add("id", requestId);
                rpcResponse.add("result", parseResult);
                protocolOutput.println(JSON.toJson(rpcResponse));
            } else {
                protocolOutput.println(JSON.toJson(parseResult));
            }
            return 0;
        } catch (Exception error) {
            String message = error.getMessage() == null ? error.getClass().getSimpleName() : error.getMessage();
            if (rpcMode) {
                writeRpcError(requestId, -32001, message);
                return 0;
            }
            System.err.println("Pilot bridge failed: " + message);
            return 1;
        }
    }

    private static JsonObject parseWorkspace(JsonObject request) throws Exception {
        JsonArray requestedFiles = request.getAsJsonArray("files");
        if (requestedFiles == null) {
            throw new IllegalArgumentException("request must include a files array");
        }

        SysMLInteractive interactive = SysMLInteractive.createInstance();
        interactive.setVerbose(false);
        String libraryDirectory = System.getenv("SYSML_PILOT_LIBRARY");
        if (libraryDirectory != null && !libraryDirectory.isBlank()) {
            interactive.loadLibrary(Path.of(libraryDirectory).toAbsolutePath().normalize().toString());
        }

        List<SourceResource> sourceResources = new ArrayList<>();
        Set<String> sourcePaths = new HashSet<>();
        for (JsonElement sourceElement : requestedFiles) {
            if (!sourceElement.isJsonObject()) {
                throw new IllegalArgumentException("each files entry must be an object");
            }
            JsonObject sourceFile = sourceElement.getAsJsonObject();
            String sourcePath = requiredString(sourceFile, "path");
            String sourceText = requiredStringAllowEmpty(sourceFile, "text");
            Path absolutePath = Path.of(sourcePath).toAbsolutePath().normalize();
            String normalizedPath = absolutePath.toString();
            if (!sourcePaths.add(normalizedPath)) {
                throw new IllegalArgumentException("duplicate model path: " + normalizedPath);
            }
            String lowercasePath = normalizedPath.toLowerCase(Locale.ROOT);
            if (!lowercasePath.endsWith(".sysml") && !lowercasePath.endsWith(".kerml")) {
                throw new IllegalArgumentException("unsupported model extension: " + normalizedPath);
            }

            Resource resource = interactive.createResource(normalizedPath);
            if (!(resource instanceof XtextResource)) {
                throw new IllegalStateException("Pilot did not create an Xtext resource for " + normalizedPath);
            }
            resource.load(
                    new ByteArrayInputStream(sourceText.getBytes(StandardCharsets.UTF_8)),
                    Collections.emptyMap());
            interactive.addInputResource(resource);
            interactive.addResourceToIndex(resource);
            sourceResources.add(new SourceResource(normalizedPath, sourceText, resource));
        }

        // Resolve projected references on demand; sweeping the Pilot library also evaluates
        // derived model features and is needlessly expensive for editor navigation.
        JsonObject response = new JsonObject();
        response.add("parser", parserMetadata());
        JsonArray fileResults = new JsonArray();
        for (SourceResource sourceResource : sourceResources) {
            fileResults.add(parseFile(sourceResource));
        }
        response.add("files", fileResults);
        return response;
    }

    private static void writeRpcError(JsonElement requestId, int code, String message) {
        JsonObject errorObject = new JsonObject();
        errorObject.addProperty("code", code);
        errorObject.addProperty("message", message);
        JsonObject rpcResponse = new JsonObject();
        rpcResponse.addProperty("jsonrpc", "2.0");
        rpcResponse.add("id", requestId);
        rpcResponse.add("error", errorObject);
        System.out.println(JSON.toJson(rpcResponse));
    }

    private static String stringValue(JsonElement value) {
        return value != null && value.isJsonPrimitive() && value.getAsJsonPrimitive().isString()
                ? value.getAsString()
                : null;
    }

    private static JsonObject parserMetadata() {
        JsonObject parser = new JsonObject();
        parser.addProperty("name", PILOT_NAME);
        String version = System.getenv("SYSML_PILOT_VERSION");
        if (version == null || version.isBlank()) {
            Package pilotPackage = SysMLInteractive.class.getPackage();
            version = pilotPackage == null ? null : pilotPackage.getImplementationVersion();
        }
        parser.addProperty("version", version == null || version.isBlank() ? "unknown" : version);
        JsonArray standards = new JsonArray();
        SUPPORTED_STANDARDS.forEach(standards::add);
        parser.add("standards", standards);
        return parser;
    }

    private static JsonObject parseFile(SourceResource source) throws Exception {
        JsonObject file = new JsonObject();
        file.addProperty("path", source.path);

        JsonArray symbols = new JsonArray();
        JsonArray references = new JsonArray();
        JsonArray diagnostics = new JsonArray();
        JsonArray imports = new JsonArray();
        Set<String> symbolKeys = new HashSet<>();
        Set<String> referenceKeys = new HashSet<>();
        Set<String> diagnosticKeys = new HashSet<>();
        Set<String> importNames = new HashSet<>();

        for (EObject rootObject : source.resource.getContents()) {
            collectModelData(
                    rootObject,
                    source,
                    symbols,
                    references,
                    imports,
                    symbolKeys,
                    referenceKeys,
                    importNames);
            TreeIterator<EObject> descendants = rootObject.eAllContents();
            while (descendants.hasNext()) {
                collectModelData(
                        descendants.next(),
                        source,
                        symbols,
                        references,
                        imports,
                        symbolKeys,
                        referenceKeys,
                        importNames);
            }
        }

        for (Resource.Diagnostic resourceError : source.resource.getErrors()) {
            addDiagnostic(
                    diagnostics,
                    diagnosticKeys,
                    source.path,
                    Math.max(1, resourceError.getLine()),
                    Math.max(0, resourceError.getColumn() - 1),
                    1,
                    "error",
                    resourceError.getMessage());
        }
        for (Resource.Diagnostic resourceWarning : source.resource.getWarnings()) {
            addDiagnostic(
                    diagnostics,
                    diagnosticKeys,
                    source.path,
                    Math.max(1, resourceWarning.getLine()),
                    Math.max(0, resourceWarning.getColumn() - 1),
                    1,
                    "warning",
                    resourceWarning.getMessage());
        }

        IResourceServiceProvider serviceProvider =
                IResourceServiceProvider.Registry.INSTANCE.getResourceServiceProvider(source.resource.getURI());
        if (serviceProvider == null) {
            throw new IllegalStateException("Pilot has no language service for " + source.path);
        }
        IResourceValidator validator = serviceProvider.getResourceValidator();
        List<Issue> validationIssues =
                validator.validate(source.resource, CheckMode.ALL, CancelIndicator.NullImpl);
        for (Issue issue : validationIssues) {
            int issueOffset = issue.getOffset() == null ? -1 : issue.getOffset();
            int issueLength = issue.getLength() == null ? 1 : Math.max(1, issue.getLength());
            SourcePosition issuePosition = source.positionAt(issueOffset);
            String severity = issue.getSeverity().toString().toLowerCase(Locale.ROOT);
            if (!"error".equals(severity) && !"warning".equals(severity)) {
                severity = "info";
            }
            addDiagnostic(
                    diagnostics,
                    diagnosticKeys,
                    source.path,
                    issuePosition.line,
                    issuePosition.column,
                    issueLength,
                    severity,
                    issue.getMessage());
        }

        file.add("symbols", symbols);
        file.add("references", references);
        file.add("diagnostics", diagnostics);
        file.add("imports", imports);
        return file;
    }

    private static void collectModelData(
            EObject modelElement,
            SourceResource source,
            JsonArray symbols,
            JsonArray references,
            JsonArray imports,
            Set<String> symbolKeys,
            Set<String> referenceKeys,
            Set<String> importNames) {
        String declaredName = declaredName(modelElement);
        String elementClassName = modelElement.eClass().getName();
        // Bare references carry a target name but are not workspace declarations.
        if (declaredName != null
                && !declaredName.isBlank()
                && !"ReferenceUsage".equals(elementClassName)) {
            INode nameNode = featureNode(modelElement, "declaredName");
            SourcePosition namePosition = nodePosition(nameNode, source, declaredName);
            String elementKind = kindName(elementClassName);
            String symbolKey = namePosition.line + ":" + namePosition.column + ":" + declaredName + ":" + elementKind;
            if (symbolKeys.add(symbolKey)) {
                JsonObject symbol = new JsonObject();
                symbol.addProperty("name", declaredName);
                symbol.addProperty("kind", elementKind);
                symbol.add("range", range(namePosition, declaredName.length()));
                String containerName = nearestContainerName(modelElement.eContainer());
                if (containerName != null) {
                    symbol.addProperty("container", containerName);
                }
                String signature = signature(modelElement);
                if (signature != null) {
                    symbol.addProperty("signature", signature);
                }
                symbols.add(symbol);
            }
        }

        for (EReference modelReference : modelElement.eClass().getEAllReferences()) {
            if (modelReference.isContainment()) {
                continue;
            }
            Object referencedValue = modelElement.eGet(modelReference, true);
            List<?> targets = referencedValue instanceof Iterable<?>
                    ? iterableValues((Iterable<?>) referencedValue)
                    : referencedValue == null ? List.of() : List.of(referencedValue);
            List<INode> referenceNodes = NodeModelUtils.findNodesForFeature(modelElement, modelReference);
            int targetIndex = 0;
            for (Object targetValue : targets) {
                INode referenceNode = referenceNodes.isEmpty()
                        ? NodeModelUtils.getNode(modelElement)
                        : referenceNodes.get(Math.min(targetIndex, referenceNodes.size() - 1));
                targetIndex++;
                if (!(targetValue instanceof EObject targetElement) || targetElement.eIsProxy()) {
                    continue;
                }
                String targetName = declaredName(targetElement);
                if (targetName == null || targetName.isBlank()) {
                    continue;
                }
                SourcePosition referencePosition = nodePosition(referenceNode, source, targetName);
                String relationship = relationshipName(modelElement, modelReference);
                String referenceSource = declaredName(modelElement);
                if (referenceSource == null) {
                    referenceSource = nearestContainerName(modelElement.eContainer());
                }
                String referenceKey = referencePosition.line + ":"
                        + referencePosition.column + ":" + targetName + ":" + relationship + ":" + referenceSource;
                if (referenceKeys.add(referenceKey)) {
                    JsonObject reference = new JsonObject();
                    reference.addProperty("name", targetName);
                    reference.add("range", range(referencePosition, targetName.length()));
                    reference.addProperty("relation", relationship);
                    if (referenceSource != null) {
                        reference.addProperty("source", referenceSource);
                    }
                    references.add(reference);
                }

                if (modelElement.eClass().getName().contains("Import")) {
                    String qualifiedImport = qualifiedName(targetElement);
                    if (importNames.add(qualifiedImport)) {
                        imports.add(qualifiedImport);
                    }
                }
            }
        }
    }

    private static List<?> iterableValues(Iterable<?> values) {
        List<Object> result = new ArrayList<>();
        values.forEach(result::add);
        return result;
    }

    private static String declaredName(EObject modelElement) {
        EStructuralFeature nameFeature = modelElement.eClass().getEStructuralFeature("declaredName");
        if (!(nameFeature instanceof EAttribute)) {
            return null;
        }
        Object nameValue = modelElement.eGet(nameFeature, false);
        return nameValue instanceof String ? (String) nameValue : null;
    }

    private static String nearestContainerName(EObject container) {
        EObject currentElement = container;
        while (currentElement != null) {
            String name = declaredName(currentElement);
            if (name != null && !name.isBlank()) {
                return name;
            }
            currentElement = currentElement.eContainer();
        }
        return null;
    }

    private static String qualifiedName(EObject modelElement) {
        List<String> nameSegments = new ArrayList<>();
        EObject currentElement = modelElement;
        while (currentElement != null) {
            String name = declaredName(currentElement);
            if (name != null && !name.isBlank()) {
                nameSegments.add(name);
            }
            currentElement = currentElement.eContainer();
        }
        Collections.reverse(nameSegments);
        return String.join("::", nameSegments);
    }

    private static INode featureNode(EObject modelElement, String featureName) {
        EStructuralFeature feature = modelElement.eClass().getEStructuralFeature(featureName);
        if (feature == null) {
            return NodeModelUtils.getNode(modelElement);
        }
        List<INode> nodes = NodeModelUtils.findNodesForFeature(modelElement, feature);
        return nodes.isEmpty() ? NodeModelUtils.getNode(modelElement) : nodes.get(0);
    }

    private static SourcePosition nodePosition(INode node, SourceResource source, String token) {
        if (node == null) {
            return new SourcePosition(1, 0);
        }
        int nodeOffset = node.getOffset();
        String nodeText = node.getText();
        int tokenOffset = nodeText.indexOf(token);
        int startOffset = tokenOffset < 0 ? nodeOffset : nodeOffset + tokenOffset;
        return source.positionAt(startOffset);
    }

    private static String signature(EObject modelElement) {
        INode node = NodeModelUtils.getNode(modelElement);
        if (node == null) {
            return null;
        }
        String text = node.getText().strip();
        if (text.isEmpty()) {
            return null;
        }
        int lineEnd = text.indexOf('\n');
        return lineEnd < 0 ? text : text.substring(0, lineEnd).stripTrailing();
    }

    private static String kindName(String eClassName) {
        if ("Package".equals(eClassName)) {
            return "package";
        }
        if (eClassName.endsWith("Definition")) {
            return camelToSnake(eClassName.substring(0, eClassName.length() - "Definition".length())) + "_def";
        }
        if (eClassName.endsWith("Usage")) {
            return camelToSnake(eClassName.substring(0, eClassName.length() - "Usage".length())) + "_usage";
        }
        return camelToSnake(eClassName);
    }

    private static String relationshipName(EObject sourceElement, EReference modelReference) {
        String className = sourceElement.eClass().getName();
        if (className.startsWith("Satisfy")) {
            return "satisfy";
        }
        if (className.startsWith("Verify")) {
            return "verify";
        }
        if (className.startsWith("Allocate")) {
            return "allocate";
        }
        if (className.startsWith("Trace")) {
            return "trace";
        }
        if (className.startsWith("Refine")) {
            return "refine";
        }
        if (className.startsWith("Redefinition") || className.startsWith("Redefine")) {
            return "redefines";
        }
        if (className.startsWith("Specialization") || className.startsWith("Specialize")) {
            return "specializes";
        }
        if (className.startsWith("Transition")) {
            return "transition";
        }
        if (className.contains("Import")) {
            return "import";
        }
        if ("type".equals(modelReference.getName())) {
            return "typed_by";
        }
        return camelToSnake(modelReference.getName());
    }

    private static String camelToSnake(String value) {
        return value.replaceAll("([a-z0-9])([A-Z])", "$1_$2").toLowerCase(Locale.ROOT);
    }

    private static void addDiagnostic(
            JsonArray diagnostics,
            Set<String> diagnosticKeys,
            String filePath,
            int line,
            int column,
            int length,
            String severity,
            String message) {
        String diagnosticKey = line + ":" + column + ":" + severity + ":" + message;
        if (!diagnosticKeys.add(diagnosticKey)) {
            return;
        }
        JsonObject diagnostic = new JsonObject();
        diagnostic.add("range", range(new SourcePosition(line, column), length));
        diagnostic.addProperty("severity", severity);
        diagnostic.addProperty("message", message == null ? "Pilot validation issue" : message);
        diagnostic.addProperty("source", PILOT_NAME);
        diagnostics.add(diagnostic);
    }

    private static JsonObject range(SourcePosition position, int length) {
        JsonObject range = new JsonObject();
        range.addProperty("line", Math.max(1, position.line));
        range.addProperty("col", Math.max(0, position.column));
        range.addProperty("end_col", Math.max(0, position.column) + Math.max(1, length));
        return range;
    }

    private static String requiredString(JsonObject object, String propertyName) {
        JsonElement value = object.get(propertyName);
        if (value == null || value.isJsonNull() || !value.isJsonPrimitive()
                || !value.getAsJsonPrimitive().isString() || value.getAsString().isBlank()) {
            throw new IllegalArgumentException("files entries require a non-empty " + propertyName);
        }
        return value.getAsString();
    }

    private static String requiredStringAllowEmpty(JsonObject object, String propertyName) {
        JsonElement value = object.get(propertyName);
        if (value == null || value.isJsonNull() || !value.isJsonPrimitive()
                || !value.getAsJsonPrimitive().isString()) {
            throw new IllegalArgumentException("files entries require a string " + propertyName);
        }
        return value.getAsString();
    }

    private static final class SourceResource {
        private final String path;
        private final String text;
        private final Resource resource;
        private final int[] lineStarts;

        private SourceResource(String path, String text, Resource resource) {
            this.path = path;
            this.text = text;
            this.resource = resource;
            List<Integer> lineStartOffsets = new ArrayList<>();
            lineStartOffsets.add(0);
            for (int offset = 0; offset < text.length(); offset++) {
                if (text.charAt(offset) == '\n') {
                    lineStartOffsets.add(offset + 1);
                }
            }
            this.lineStarts = lineStartOffsets.stream().mapToInt(Integer::intValue).toArray();
        }

        private SourcePosition positionAt(int requestedOffset) {
            int boundedOffset = Math.max(0, Math.min(requestedOffset, text.length()));
            int lineIndex = Arrays.binarySearch(lineStarts, boundedOffset);
            if (lineIndex < 0) {
                lineIndex = -lineIndex - 2;
            }
            return new SourcePosition(lineIndex + 1, boundedOffset - lineStarts[lineIndex]);
        }
    }

    private static final class SourcePosition {
        private final int line;
        private final int column;

        private SourcePosition(int line, int column) {
            this.line = line;
            this.column = column;
        }
    }
}
