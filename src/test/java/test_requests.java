package test;

import io.restassured.RestAssured;
import io.restassured.http.ContentType;
import io.restassured.response.Response;
import org.testng.Assert;
import org.testng.annotations.BeforeClass;
import org.testng.annotations.Test;

import static io.restassured.RestAssured.given;
import static org.hamcrest.Matchers.*;

public class RestfulServices {

    @BeforeClass
    public void setup() {
        RestAssured.baseURI = "https://practice-automation.com/api";
        RestAssured.basePath = "/brands";
    }

    @Test
    public void get_brands_test() {
        given()
            .when()
            .get()
            .then()
            .statusCode(200);
    }

    @Test
    public void create_brand_test() {
        String jsonBody = "{" +
                "\"name\": \"Nite Ize\"," +
                "\"description\": \"Nite Ize products are built to solve problems, inspire your imagination, and make your everyday life easier.\"," +
                "\"website\": \"http://niteize.com\"," +
                "\"image\": \"https://i.ibb.co/6803P0m/nite-ize-logo.png\"" +
                "}";

        given()
            .contentType(ContentType.JSON)
            .body(jsonBody)
            .when()
            .post()
            .then()
            .statusCode(201)
            .body("name", equalTo("Nite Ize"))
            .body("description", containsString("Nite Ize products"))
            .body("website", equalTo("http://niteize.com"));
    }

    @Test(dependsOnMethods = "create_brand_test")
    public void get_brands_and_verify_response_data() {
        Response response = given()
            .when()
            .get();

        Assert.assertEquals(response.getStatusCode(), 200);
        
        // Find the brand we just created (assuming it's at the end or we search by name)
        response.then().body("name", hasItem("Nite Ize"));
    }

    @Test(dependsOnMethods = "get_brands_and_verify_response_data")
    public void delete_brand_test() {
        // First get the ID of the brand to delete
        Response response = given().when().get();
        int id = response.jsonPath().getInt("find { it.name == 'Nite Ize' }.id");

        given()
            .when()
            .delete("/" + id)
            .then()
            .statusCode(204);
    }
}
