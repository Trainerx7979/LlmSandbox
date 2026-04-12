```Json

{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Agent Response Schema",
  "type": "object",
  "required": [
    "actions",
    "mood",
    "memory_updates",
    "long_term_goals",
    "short_term_goals",
    "relationship_changes",
    "metadata"
  ],
  "additionalProperties": false,
  "properties": {
    "actions": {
      "type": "array",
      "minItems": 1,
      "items": {
        "oneOf": [
          {
            "type": "object",
            "required": [
              "type",
              "to",
              "priority"
            ],
            "additionalProperties": false,
            "properties": {
              "type": {
                "const": "move"
              },
              "to": {
                "type": "object",
                "required": [
                  "x",
                  "y"
                ],
                "additionalProperties": false,
                "properties": {
                  "x": {
                    "type": "number"
                  },
                  "y": {
                    "type": "number"
                  }
                }
              },
              "priority": {
                "type": "integer"
              }
            }
          },
          {
            "type": "object",
            "required": [
              "type",
              "target",
              "text",
              "priority"
            ],
            "additionalProperties": false,
            "properties": {
              "type": {
                "const": "say"
              },
              "target": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "text": {
                "type": "string"
              },
              "priority": {
                "type": "integer"
              }
            }
          },
          {
            "type": "object",
            "required": [
              "type",
              "target",
              "priority"
            ],
            "additionalProperties": false,
            "properties": {
              "type": {
                "const": "attack"
              },
              "target": {
                "type": "string"
              },
              "priority": {
                "type": "integer"
              }
            }
          },
          {
            "type": "object",
            "required": [
              "type",
              "item_id",
              "priority"
            ],
            "additionalProperties": false,
            "properties": {
              "type": {
                "const": "pick_up"
              },
              "item_id": {
                "type": "string"
              },
              "priority": {
                "type": "integer"
              }
            }
          },
          {
            "type": "object",
            "required": [
              "type",
              "item_id",
              "priority"
            ],
            "additionalProperties": false,
            "properties": {
              "type": {
                "const": "drop"
              },
              "item_id": {
                "type": "string"
              },
              "priority": {
                "type": "integer"
              }
            }
          },
          {
            "type": "object",
            "required": [
              "type",
              "item_id",
              "priority"
            ],
            "additionalProperties": false,
            "properties": {
              "type": {
                "const": "use"
              },
              "item_id": {
                "type": "string"
              },
              "priority": {
                "type": "integer"
              }
            }
          },
          {
            "type": "object",
            "required": [
              "type",
              "item_id",
              "target",
              "priority"
            ],
            "additionalProperties": false,
            "properties": {
              "type": {
                "const": "give"
              },
              "item_id": {
                "type": "string"
              },
              "target": {
                "type": "string"
              },
              "priority": {
                "type": "integer"
              }
            }
          },
          {
            "type": "object",
            "required": [
              "type",
              "duration",
              "priority"
            ],
            "additionalProperties": false,
            "properties": {
              "type": {
                "const": "wait"
              },
              "duration": {
                "type": "number"
              },
              "priority": {
                "type": "integer"
              }
            }
          },
          {
            "type": "object",
            "required": [
              "type",
              "priority"
            ],
            "additionalProperties": false,
            "properties": {
              "type": {
                "const": "sleep"
              },
              "priority": {
                "type": "integer"
              }
            }
          }
        ]
      }
    },
    "mood": {
      "type": "string",
      "enum": [
        "calm",
        "happy",
        "sad",
        "angry",
        "fearful",
        "curious",
        "bored",
        "excited",
        "tired",
        "hungry"
      ]
    },
    "memory_updates": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "long_term_goals": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "short_term_goals": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "relationship_changes": {
      "type": "object",
      "additionalProperties": {
        "type": "number"
      }
    },
    "metadata": {
      "type": "object",
      "required": [
        "reasoning"
      ],
      "additionalProperties": false,
      "properties": {
        "reasoning": {
          "type": "string"
        }
      }
    }
  }
}
```
