# API

## Submit a problem

Multipart:
```http
POST /api/problems
```

Fields:
- title
- description
- latitude
- longitude
- evidence (one or more image files)

JSON without evidence is also accepted.

## Analyze

```http
POST /api/problems/<id>/analyze
```

Returns:
- classification
- skills
- evidence analysis
- duplicate reports
- priority
- university matches

## Universities

```http
GET /api/universities
POST /api/universities
```

POST example:
```json
{
  "name": "Example University",
  "city": "Trichy",
  "description": "IoT and environmental engineering university",
  "capacity": 10,
  "faculty": [
    {
      "name": "Dr A",
      "department": "CSE",
      "expertise": "IoT, machine learning, GIS"
    }
  ],
  "labs": [
    {
      "name": "IoT Lab",
      "facilities": "sensor networks, embedded systems"
    }
  ],
  "projects": [
    {
      "title": "Water monitoring",
      "description": "IoT groundwater monitoring"
    }
  ]
}
```

## Projects

```http
POST /api/projects
GET /api/projects
PATCH /api/projects/<id>
```
