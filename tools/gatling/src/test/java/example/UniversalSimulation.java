package example;

import static io.gatling.javaapi.core.CoreDsl.*;
import static io.gatling.javaapi.http.HttpDsl.*;

import io.gatling.javaapi.core.*;
import io.gatling.javaapi.http.*;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.HashMap;
import java.util.Arrays;
import java.util.Iterator;
import java.util.ArrayList;
import java.util.function.Supplier;
import java.util.stream.Stream;

public class UniversalSimulation extends Simulation {

    // Basic configuration
    private static final String baseUrl = System.getProperty("baseUrl", "https://api-ecomm.gatling.io");
    private static final int vu = Integer.getInteger("vu", 1);
    private static final int duration = Integer.getInteger("duration", 60);
    private static final double rps = Double.parseDouble(System.getProperty("rps", "1.0"));
    
    // Feeder configuration
    private static final String feederType = System.getProperty("feederType", "none");
    private static final String feederData = System.getProperty("feederData", "");
    private static final String csvFile = System.getProperty("csvFile", "");
    
    // Request configuration  
    private static final String endpoint = System.getProperty("endpoint", "/session");
    // Optional: comma-separated list of endpoints to chain within the scenario
    private static final String endpoints = System.getProperty("endpoints", "");
    private static final String method = System.getProperty("method", "GET");
    private static final String authToken = System.getProperty("authToken", "");
    private static final String jsonBody = System.getProperty("jsonBody", "");
    private static final String headers = System.getProperty("headers", "");

    // Assertions configuration (enable/thresholds)
    // Default disabled to avoid spurious failures in smoke runs; override with -DenableAssertions=true when needed
    private static final boolean enableAssertions = Boolean.parseBoolean(System.getProperty("enableAssertions", "false"));
    private static final double failPctLt = Double.parseDouble(System.getProperty("failPctLt", "5.0"));
    private static final double p95Lt = Double.parseDouble(System.getProperty("p95Lt", "2000"));
    private static final double p99Lt = Double.parseDouble(System.getProperty("p99Lt", "0"));
    private static final double meanRtLt = Double.parseDouble(System.getProperty("meanRtLt", "0"));

    // Injection profile tuning
    private static final String injection = System.getProperty("injection", ""); // e.g., constantRps|rampRps
    private static final int rampUp = Integer.getInteger("rampUp", 0);
    private static final int holdFor = Integer.getInteger("holdFor", duration);
    private static final int rampDown = Integer.getInteger("rampDown", 0);
    private static final int toUsers = Integer.getInteger("toUsers", vu);
    private static final int pauseMs = Integer.getInteger("pauseMs", 0);

    // HTTP Protocol configuration
    private static final HttpProtocolBuilder httpProtocol = buildHttpProtocol();
    
    // Feeder configuration
    private static final FeederBuilder<?> feeder = buildFeeder();
    
    // Scenario configuration
    private static final ScenarioBuilder scenario = buildScenario();

    private static HttpProtocolBuilder buildHttpProtocol() {
        HttpProtocolBuilder protocol = http.baseUrl(baseUrl)
            .acceptHeader("application/json")
            .userAgentHeader("QA-Intelligence-Agent/1.0");
            
        // Add authentication if token provided
        if (!authToken.isEmpty()) {
            protocol = protocol.authorizationHeader("Bearer " + authToken);
        }
        
        // Add custom headers if provided
        if (!headers.isEmpty()) {
            String[] headerPairs = headers.split(",");
            for (String pair : headerPairs) {
                String[] keyValue = pair.split(":");
                if (keyValue.length == 2) {
                    protocol = protocol.header(keyValue[0].trim(), keyValue[1].trim());
                }
            }
        }
        
        return protocol;
    }

    private static FeederBuilder<?> buildFeeder() {
        switch (feederType.toLowerCase()) {
            case "csv":
                if (!csvFile.isEmpty()) {
                    return csv(csvFile).random();
                }
                break;
                
            case "users":
                // Generate user accounts dynamically
                return buildUserFeeder();
                
            case "random":
                // Generate random data
                return buildRandomFeeder();
                
            case "json":
                // Parse JSON data for complex feeders
                return buildJsonFeeder();
                
            default:
                // No feeder needed
                return null;
        }
        return null;
    }

    private static FeederBuilder<?> buildUserFeeder() {
        // Create user accounts from feederData parameter
        // Format: "user1:pass1,user2:pass2,user3:pass3"
        String[] users = feederData.split(",");
        List<Map<String, Object>> userList = Arrays.stream(users)
            .map(user -> {
                String[] credentials = user.split(":");
                Map<String, Object> userMap = new HashMap<>();
                userMap.put("username", credentials.length > 0 ? credentials[0] : "defaultUser");
                userMap.put("password", credentials.length > 1 ? credentials[1] : "defaultPass");
                userMap.put("userId", "user_" + System.currentTimeMillis() + "_" + Math.random());
                return userMap;
            })
            .collect(java.util.stream.Collectors.toList());
            
        return listFeeder(userList).circular();
    }

    private static FeederBuilder<?> buildRandomFeeder() {
        // Generate random data based on feederData specification
        // Format: "email:random@domain.com,phone:555-###-####,id:######"
        List<Map<String, Object>> randomList = Stream.generate(() -> {
            Map<String, Object> randomData = new HashMap<>();
            
            if (feederData.contains("email")) {
                randomData.put("email", "user" + Math.random() + "@test.com");
            }
            if (feederData.contains("phone")) {
                randomData.put("phone", "555-" + (int)(Math.random() * 1000) + "-" + (int)(Math.random() * 10000));
            }
            if (feederData.contains("id")) {
                randomData.put("id", String.valueOf((int)(Math.random() * 1000000)));
            }
            if (feederData.contains("account")) {
                randomData.put("accountId", "ACC_" + System.currentTimeMillis() + "_" + (int)(Math.random() * 1000));
            }
            
            return randomData;
        }).limit(100).collect(java.util.stream.Collectors.toList());
        
        return listFeeder(randomList);
    }

    private static FeederBuilder<?> buildJsonFeeder() {
        // For complex JSON-based feeders
        // This would parse feederData as JSON and create appropriate feeder
        // Implementation would depend on specific JSON structure
        List<Map<String, Object>> jsonList = Stream.generate(() -> {
            Map<String, Object> jsonData = new HashMap<>();
            // Parse feederData as JSON and populate jsonData
            // For now, basic implementation
            jsonData.put("dynamicField", "value_" + Math.random());
            return jsonData;
        }).limit(50).collect(java.util.stream.Collectors.toList());
        
        return listFeeder(jsonList);
    }

    private static String generateRequestName(String ep) {
        // Generate meaningful request names based on endpoint
        if (ep == null || ep.isEmpty()) {
            return "API Request";
        }
        
        // Remove query parameters for cleaner names
        String cleanEp = ep.split("\\?")[0];
        
        // Remove leading slash and replace path separators with spaces
        String name = cleanEp.replaceFirst("^/", "").replace("/", " ");
        
        // If still empty, use method + endpoint
        if (name.isEmpty()) {
            return method.toUpperCase() + " " + ep;
        }
        
        // Capitalize first letter and return
        return name.substring(0, 1).toUpperCase() + 
               (name.length() > 1 ? name.substring(1) : "");
    }

    private static ScenarioBuilder buildScenario() {
        ScenarioBuilder scn = scenario("Universal Performance Test");

        // Add feeder if configured
        if (feeder != null) {
            scn = scn.feed(feeder);
        }

        // If multiple endpoints provided, chain them in order
        if (!endpoints.isEmpty()) {
            String[] eps = endpoints.split(",");
            ChainBuilder chain = exec(session -> session);
            for (String e : eps) {
                String ep = e.trim();
                if (!ep.startsWith("/")) {
                    ep = "/" + ep;
                }
                HttpRequestActionBuilder req = buildHttpRequest(ep);
                chain = chain.exec(req);
                if (pauseMs > 0) {
                    chain = chain.pause(Duration.ofMillis(pauseMs));
                }
            }
            return scn.exec(chain);
        }

        // Single endpoint
        HttpRequestActionBuilder request = buildHttpRequest(endpoint);
        return scn.exec(request);
    }

    private static HttpRequestActionBuilder buildHttpRequest(String ep) {
        HttpRequestActionBuilder request;
        
        // Create request based on method with endpoint-specific names
        String requestName = generateRequestName(ep);
        switch (method.toUpperCase()) {
            case "POST":
                request = http(requestName).post(ep);
                break;
            case "PUT":
                request = http(requestName).put(ep);
                break;
            case "DELETE":
                request = http(requestName).delete(ep);
                break;
            case "PATCH":
                request = http(requestName).patch(ep);
                break;
            default:
                request = http(requestName).get(ep);
        }
        
        // Add JSON body if provided
        if (!jsonBody.isEmpty()) {
            request = request.body(StringBody(jsonBody)).asJson();
        }
        
        // Add feeder variables to request if feeder is configured
        if (feeder != null) {
            switch (feederType.toLowerCase()) {
                case "users":
                    // Use username/password from feeder
                    if (method.equals("POST") && endpoint.contains("login")) {
                        request = request.body(StringBody(
                            "{\"username\":\"#{username}\",\"password\":\"#{password}\"}"
                        )).asJson();
                    }
                    break;
                    
                case "random":
                case "json":
                    // Variables will be available as #{variableName} in templates
                    break;
            }
        }
        
        return request;
    }

    // Test execution setup
    {
        // Injection selection
        OpenInjectionStep[] openProfile;
        if (rps > 0) {
            if (rampUp > 0 || rampDown > 0 || "rampRps".equalsIgnoreCase(injection)) {
                openProfile = new OpenInjectionStep[] {
                    rampUsersPerSec(1).to(rps).during(rampUp),
                    constantUsersPerSec(rps).during(Math.max(1, holdFor)),
                    rampUsersPerSec(rps).to(1).during(rampDown)
                };
            } else {
                openProfile = new OpenInjectionStep[] { constantUsersPerSec(rps).during(duration) };
            }
        } else {
            openProfile = new OpenInjectionStep[] { atOnceUsers(vu) };
        }

        PopulationBuilder pop = scenario.injectOpen(openProfile);

        // Build assertions list conditionally
        List<Assertion> asserts = new ArrayList<>();
        if (enableAssertions) {
            if (failPctLt > 0) asserts.add(global().failedRequests().percent().lt(failPctLt));
            // Gatling Java DSL expects Integer milliseconds for response time thresholds
            if (p95Lt > 0) asserts.add(global().responseTime().percentile3().lt((int) Math.round(p95Lt)));
            if (p99Lt > 0) asserts.add(global().responseTime().percentile4().lt((int) Math.round(p99Lt)));
            if (meanRtLt > 0) asserts.add(global().responseTime().mean().lt((int) Math.round(meanRtLt)));
        }

        SetUp set = setUp(pop).protocols(httpProtocol);
        if (!asserts.isEmpty()) {
            set.assertions(asserts);
        }
    }
}
