{

&#x20; "$schema": "http://json-schema.org/draft-07/schema#",

&#x20; "title": "Agent Response Schema",

&#x20; "type": "object",

&#x20; "required": \[

&#x20;   "actions",

&#x20;   "mood",

&#x20;   "memory\_updates",

&#x20;   "long\_term\_goals",

&#x20;   "short\_term\_goals",

&#x20;   "relationship\_changes",

&#x20;   "metadata"

&#x20; ],

&#x20; "additionalProperties": false,

&#x20; "properties": {

&#x20;   "actions": {

&#x20;     "type": "array",

&#x20;     "minItems": 1,

&#x20;     "items": {

&#x20;       "oneOf": \[

&#x20;         {

&#x20;           "type": "object",

&#x20;           "required": \["type", "to", "priority"],

&#x20;           "additionalProperties": false,

&#x20;           "properties": {

&#x20;             "type": { "const": "move" },

&#x20;             "to": {

&#x20;               "type": "object",

&#x20;               "required": \["x", "y"],

&#x20;               "additionalProperties": false,

&#x20;               "properties": {

&#x20;                 "x": { "type": "number" },

&#x20;                 "y": { "type": "number" }

&#x20;               }

&#x20;             },

&#x20;             "priority": { "type": "integer" }

&#x20;           }

&#x20;         },

&#x20;         {

&#x20;           "type": "object",

&#x20;           "required": \["type", "target", "text", "priority"],

&#x20;           "additionalProperties": false,

&#x20;           "properties": {

&#x20;             "type": { "const": "say" },

&#x20;             "target": {

&#x20;               "anyOf": \[

&#x20;                 { "type": "string" },

&#x20;                 { "type": "null" }

&#x20;               ]

&#x20;             },

&#x20;             "text": { "type": "string" },

&#x20;             "priority": { "type": "integer" }

&#x20;           }

&#x20;         },

&#x20;         {

&#x20;           "type": "object",

&#x20;           "required": \["type", "target", "priority"],

&#x20;           "additionalProperties": false,

&#x20;           "properties": {

&#x20;             "type": { "const": "attack" },

&#x20;             "target": { "type": "string" },

&#x20;             "priority": { "type": "integer" }

&#x20;           }

&#x20;         },

&#x20;         {

&#x20;           "type": "object",

&#x20;           "required": \["type", "item\_id", "priority"],

&#x20;           "additionalProperties": false,

&#x20;           "properties": {

&#x20;             "type": { "const": "pick\_up" },

&#x20;             "item\_id": { "type": "string" },

&#x20;             "priority": { "type": "integer" }

&#x20;           }

&#x20;         },

&#x20;         {

&#x20;           "type": "object",

&#x20;           "required": \["type", "item\_id", "priority"],

&#x20;           "additionalProperties": false,

&#x20;           "properties": {

&#x20;             "type": { "const": "drop" },

&#x20;             "item\_id": { "type": "string" },

&#x20;             "priority": { "type": "integer" }

&#x20;           }

&#x20;         },

&#x20;         {

&#x20;           "type": "object",

&#x20;           "required": \["type", "item\_id", "priority"],

&#x20;           "additionalProperties": false,

&#x20;           "properties": {

&#x20;             "type": { "const": "use" },

&#x20;             "item\_id": { "type": "string" },

&#x20;             "priority": { "type": "integer" }

&#x20;           }

&#x20;         },

&#x20;         {

&#x20;           "type": "object",

&#x20;           "required": \["type", "item\_id", "target", "priority"],

&#x20;           "additionalProperties": false,

&#x20;           "properties": {

&#x20;             "type": { "const": "give" },

&#x20;             "item\_id": { "type": "string" },

&#x20;             "target": { "type": "string" },

&#x20;             "priority": { "type": "integer" }

&#x20;           }

&#x20;         },

&#x20;         {

&#x20;           "type": "object",

&#x20;           "required": \["type", "duration", "priority"],

&#x20;           "additionalProperties": false,

&#x20;           "properties": {

&#x20;             "type": { "const": "wait" },

&#x20;             "duration": { "type": "number" },

&#x20;             "priority": { "type": "integer" }

&#x20;           }

&#x20;         },

&#x20;         {

&#x20;           "type": "object",

&#x20;           "required": \["type", "priority"],

&#x20;           "additionalProperties": false,

&#x20;           "properties": {

&#x20;             "type": { "const": "sleep" },

&#x20;             "priority": { "type": "integer" }

&#x20;           }

&#x20;         }

&#x20;       ]

&#x20;     }

&#x20;   },

&#x20;   "mood": {

&#x20;     "type": "string",

&#x20;     "enum": \[

&#x20;       "calm",

&#x20;       "happy",

&#x20;       "sad",

&#x20;       "angry",

&#x20;       "fearful",

&#x20;       "curious",

&#x20;       "bored",

&#x20;       "excited",

&#x20;       "tired",

&#x20;       "hungry"

&#x20;     ]

&#x20;   },

&#x20;   "memory\_updates": {

&#x20;     "type": "array",

&#x20;     "items": { "type": "string" }

&#x20;   },

&#x20;   "long\_term\_goals": {

&#x20;     "type": "array",

&#x20;     "items": { "type": "string" }

&#x20;   },

&#x20;   "short\_term\_goals": {

&#x20;     "type": "array",

&#x20;     "items": { "type": "string" }

&#x20;   },

&#x20;   "relationship\_changes": {

&#x20;     "type": "object",

&#x20;     "additionalProperties": { "type": "number" }

&#x20;   },

&#x20;   "metadata": {

&#x20;     "type": "object",

&#x20;     "required": \["reasoning"],

&#x20;     "additionalProperties": false,

&#x20;     "properties": {

&#x20;       "reasoning": { "type": "string" }

&#x20;     }

&#x20;   }

&#x20; }

}





Example Valid Response:
{

&#x20; "actions": \[

&#x20;   { "type": "move", "to": { "x": 12.5, "y": -3.0 }, "priority": 1 },

&#x20;   { "type": "say", "target": "npc\_42", "text": "We should avoid the patrol.", "priority": 2 },

&#x20;   { "type": "pick\_up", "item\_id": "gold\_coin\_7", "priority": 2 },

&#x20;   { "type": "wait", "duration": 5, "priority": 5 }

&#x20; ],

&#x20; "mood": "curious",

&#x20; "memory\_updates": \[

&#x20;   "Found a hidden chest behind the waterfall",

&#x20;   "NPC\_42 warned about night patrols"

&#x20; ],

&#x20; "long\_term\_goals": \[

&#x20;   "Secure the eastern outpost",

&#x20;   "Gain trust of the merchant guild"

&#x20; ],

&#x20; "short\_term\_goals": \[

&#x20;   "Retrieve the map from the chest",

&#x20;   "Avoid patrols until dawn"

&#x20; ],

&#x20; "relationship\_changes": {

&#x20;   "npc\_42": 0.15,

&#x20;   "merchant\_01": -0.05

&#x20; },

&#x20; "metadata": {

&#x20;   "reasoning": "Move to cover, inform NPC\_42, pick up visible loot, then wait to avoid patrol timing."

&#x20; }

}

