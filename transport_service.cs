var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

var vehicles = new[]
{
    new { id = "v1", driver = "Иван", status = "free" },
    new { id = "v2", driver = "Петр", status = "free" }
};

app.MapGet("/vehicles/available", () => vehicles.Where(v => v.status == "free"));

app.Run();