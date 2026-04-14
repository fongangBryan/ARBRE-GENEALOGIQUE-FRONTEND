# Documentation API — Genealogie App

**Base URL** : `http://localhost:8000/api/v1`  
**Swagger UI** : `http://localhost:8000/api/docs`  
**ReDoc** : `http://localhost:8000/api/redoc`

---

## Table des matières

1. [Authentification](#1-authentification)
2. [Système de rôles et permissions](#2-système-de-rôles-et-permissions)
3. [Utiliser les tokens JWT](#3-utiliser-les-tokens-jwt)
4. [Module AUTH](#4-module-auth)
5. [Module USERS](#5-module-users)
6. [Module PERSONS](#6-module-persons)
7. [Module RELATIONSHIPS](#7-module-relationships)
8. [Module TREE](#8-module-tree)
9. [Module EVENTS](#9-module-events)
10. [Module MEDIA](#10-module-media)
11. [Module ADMIN](#11-module-admin)
12. [Codes d'erreur](#12-codes-derreur)
13. [Workflow complet — exemple pas à pas](#13-workflow-complet--exemple-pas-à-pas)

---

## 1. Authentification

L'API utilise **JWT (JSON Web Tokens)** avec deux tokens :

| Token | Durée de vie | Usage |
|---|---|---|
| `access_token` | 15 minutes | Autoriser chaque requête |
| `refresh_token` | 7 jours | Obtenir un nouvel access_token |

### Comment s'authentifier

1. Appelez `POST /auth/login` pour obtenir les tokens
2. Ajoutez le header suivant à chaque requête protégée :
   ```
   Authorization: Bearer <access_token>
   ```
3. Quand l'access_token expire (erreur 401), appelez `POST /auth/refresh`

---

## 2. Système de rôles et permissions

Chaque utilisateur possède un rôle qui détermine ce qu'il peut faire :

| Rôle | Lecture | Création/Modification | Suppression | Admin |
|---|:---:|:---:|:---:|:---:|
| **READER** | ✅ | ❌ | ❌ | ❌ |
| **EDITOR** | ✅ | ✅ | ❌ | ❌ |
| **ADMIN** | ✅ | ✅ | ✅ | ✅ |

> Les nouveaux inscrits obtiennent automatiquement le rôle **READER**.  
> Seul un ADMIN peut promouvoir un utilisateur en EDITOR ou ADMIN.

### Niveaux de confidentialité des personnes

Chaque personne dans l'arbre a un `privacy_level` :

| Niveau | Qui peut voir |
|---|---|
| `public` | Tout utilisateur connecté |
| `family` | Créateur + EDITORs + utilisateurs avec ACL |
| `private` | Créateur uniquement + utilisateurs avec ACL explicite |

---

## 3. Utiliser les tokens JWT

### Dans le fichier `api.http` (VS Code REST Client)

```http
### 1. Se connecter
POST http://localhost:8000/api/v1/auth/login
Content-Type: application/json

{
  "email": "admin@genealogie.com",
  "password": "Admin123!"
}

### 2. Copier l'access_token dans la variable ci-dessous
@accessToken = eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

### 3. Utiliser le token dans les requêtes suivantes
GET http://localhost:8000/api/v1/users/me
Authorization: Bearer {{accessToken}}
```

### Dans Swagger UI

1. Ouvrez `http://localhost:8000/api/docs`
2. Cliquez sur le bouton **Authorize** (cadenas en haut à droite)
3. Dans le champ `HTTPBearer`, collez uniquement le token (sans `Bearer `)
4. Cliquez **Authorize** puis **Close**
5. Tous les endpoints protégés sont maintenant accessibles

---

## 4. Module AUTH

### `POST /auth/register` — Créer un compte

**Accès** : Public (sans token)

**Corps de la requête** :
```json
{
  "email": "jean.dupont@example.com",
  "password": "MonMotDePasse123!",
  "first_name": "Jean",
  "last_name": "Dupont"
}
```

**Réponse 200** :
```json
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "token_type": "bearer"
}
```

**Contraintes** :
- `password` : minimum 8 caractères
- `email` : format valide et unique

---

### `POST /auth/login` — Se connecter

**Accès** : Public

**Corps de la requête** :
```json
{
  "email": "jean.dupont@example.com",
  "password": "MonMotDePasse123!"
}
```

**Avec 2FA activé** :
```json
{
  "email": "jean.dupont@example.com",
  "password": "MonMotDePasse123!",
  "two_factor_code": "123456"
}
```

**Réponse 200 (sans 2FA)** :
```json
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "requires_2fa": false
}
```

**Réponse 200 (2FA requis)** :
```json
{
  "access_token": "",
  "refresh_token": "",
  "requires_2fa": true,
  "user_id": "550e8400-e29b-41d4-a716-446655440000"
}
```
> Si `requires_2fa: true`, relancez la requête en ajoutant le `two_factor_code`.

---

### `POST /auth/refresh` — Renouveler le token

**Accès** : Public

```json
{
  "refresh_token": "eyJhbGci..."
}
```

**Réponse 200** :
```json
{
  "access_token": "eyJhbGci...(nouveau)",
  "refresh_token": "eyJhbGci...(nouveau)",
  "token_type": "bearer"
}
```

---

### `POST /auth/logout` — Se déconnecter

**Accès** : Authentifié  
**Header** : `Authorization: Bearer <token>`

```json
{ "message": "Logged out successfully" }
```

---

### `POST /auth/setup-2fa` — Configurer la 2FA

**Accès** : Authentifié

**Réponse** :
```json
{
  "secret": "JBSWY3DPEHPK3PXP",
  "qr_code": "data:image/png;base64,iVBOR..."
}
```
> Scannez le QR code avec **Google Authenticator** ou **Authy**, puis validez avec `/auth/verify-2fa`.

---

### `POST /auth/verify-2fa?token=123456` — Activer la 2FA

**Accès** : Authentifié  
**Paramètre** : `token` (code à 6 chiffres de l'application)

```json
{ "message": "2FA enabled successfully" }
```

---

## 5. Module USERS

### `GET /users/me` — Mon profil

**Accès** : Authentifié

**Réponse** :
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "jean.dupont@example.com",
  "first_name": "Jean",
  "last_name": "Dupont",
  "role": "reader",
  "is_active": true,
  "is_verified": false,
  "is_2fa_enabled": false,
  "created_at": "2026-04-13T10:00:00Z",
  "last_login": "2026-04-13T12:00:00Z"
}
```

---

### `PUT /users/me` — Modifier mon profil

**Accès** : Authentifié

```json
{
  "first_name": "Jean-Pierre",
  "last_name": "Dupont",
  "email": "nouveau@example.com"
}
```
> Tous les champs sont optionnels — envoyez uniquement ce que vous voulez modifier.

---

### `PUT /users/me/password` — Changer mon mot de passe

**Accès** : Authentifié

```json
{
  "current_password": "AncienMotDePasse123!",
  "new_password": "NouveauMotDePasse456!"
}
```

---

### `DELETE /users/me` — Supprimer mon compte

**Accès** : Authentifié  
Effectue un **soft delete** (désactivation) — les données sont conservées.

---

## 6. Module PERSONS

### `GET /persons` — Lister les personnes

**Accès** : Authentifié (tous rôles)

**Paramètres de requête** :
| Paramètre | Type | Défaut | Description |
|---|---|---|---|
| `search` | string | - | Recherche par prénom ou nom |
| `page` | int | 1 | Numéro de page |
| `limit` | int | 20 | Résultats par page (max 100) |

**Exemples** :
```
GET /persons
GET /persons?search=Marie
GET /persons?page=2&limit=10
GET /persons?search=Dupont&page=1&limit=5
```

**Réponse** :
```json
{
  "items": [
    {
      "id": "550e8400-...",
      "first_name": "Marie",
      "last_name": "Curie",
      "gender": "female",
      "birth_date": "1867-11-07",
      "birth_place": "Varsovie",
      "death_date": "1934-07-04",
      "is_living": false,
      "privacy_level": "public"
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 20,
  "pages": 1
}
```

---

### `POST /persons` — Créer une personne

**Accès** : EDITOR, ADMIN

```json
{
  "first_name": "Marie",
  "last_name": "Curie",
  "maiden_name": "Sklodowska",
  "gender": "female",
  "birth_date": "1867-11-07",
  "birth_place": "Varsovie, Pologne",
  "death_date": "1934-07-04",
  "death_place": "Passy, France",
  "is_living": false,
  "biography": "Physicienne et chimiste polonaise naturalisée française.",
  "occupation": "Physicienne, chimiste",
  "nationality": "Française",
  "privacy_level": "public"
}
```

**Champs obligatoires** : `first_name`, `last_name`  
**Champs optionnels** : tous les autres

**Formats de date acceptés** :
```
"1867"          → année seulement
"1867-11"       → année et mois
"1867-11-07"    → date complète
```

**Valeurs de `gender`** : `male` | `female` | `other`  
**Valeurs de `privacy_level`** : `public` | `family` | `private`

---

### `GET /persons/{person_id}` — Détail d'une personne

**Accès** : Authentifié (selon ACL)

```
GET /persons/550e8400-e29b-41d4-a716-446655440000
```

---

### `PUT /persons/{person_id}` — Modifier une personne

**Accès** : EDITOR (créateur ou ACL write), ADMIN

```json
{
  "biography": "Biographie mise à jour...",
  "death_date": "1934-07-04",
  "is_living": false
}
```
> Envoyez uniquement les champs à modifier.

---

### `DELETE /persons/{person_id}` — Supprimer une personne

**Accès** : ADMIN uniquement

---

## 7. Module RELATIONSHIPS

Les relations permettent de construire l'arbre généalogique.  
Il existe **2 types** de relations :

| Type | Description | Champs spécifiques |
|---|---|---|
| `parent_child` | Lien parent → enfant | `child_type` |
| `couple` | Lien conjoint | `marriage_date`, `marriage_place`, `divorce_date` |

### `POST /relationships` — Créer une relation

**Accès** : EDITOR (avec droits ACL sur les 2 personnes), ADMIN

#### Relation parent-enfant
```json
{
  "type": "parent_child",
  "person_id_1": "uuid-du-parent",
  "person_id_2": "uuid-de-lenfant",
  "child_type": "biological"
}
```

**Valeurs de `child_type`** :
| Valeur | Signification |
|---|---|
| `biological` | Enfant biologique |
| `adoptive` | Enfant adopté |
| `step` | Beau-fils / belle-fille |
| `guardian` | Sous tutelle |

#### Relation couple
```json
{
  "type": "couple",
  "person_id_1": "uuid-personne-1",
  "person_id_2": "uuid-personne-2",
  "marriage_date": "1895-07-26",
  "marriage_place": "Paris, France",
  "divorce_date": null
}
```

> ⚠️ Le système détecte automatiquement les **cycles** dans l'arbre.  
> Ex : si A est parent de B, vous ne pouvez pas mettre B comme parent de A.

---

### `GET /relationships/person/{person_id}` — Relations d'une personne

```
GET /relationships/person/550e8400-...
GET /relationships/person/550e8400-...?relationship_type=parent_child
GET /relationships/person/550e8400-...?relationship_type=couple
```

---

### `GET /relationships/between/{id1}/{id2}` — Relation entre deux personnes

Vérifie si une relation directe existe entre deux personnes.

---

### `GET /relationships/{person_id}/parents` — Parents d'une personne
### `GET /relationships/{person_id}/children` — Enfants d'une personne
### `GET /relationships/{person_id}/spouses` — Conjoints d'une personne

---

### `PUT /relationships/{relationship_id}` — Modifier une relation

```json
{
  "divorce_date": "1910-03-15",
  "marriage_place": "Paris, France"
}
```

---

### `DELETE /relationships/{relationship_id}` — Supprimer une relation

**Accès** : EDITOR (avec droits ACL), ADMIN

---

## 8. Module TREE

Tous les endpoints retournent un graphe au **format Cytoscape.js** :

```json
{
  "nodes": [
    {
      "data": {
        "id": "550e8400-...",
        "label": "CURIE Marie",
        "birth_date": "1867-11-07",
        "is_living": false
      }
    }
  ],
  "edges": [
    {
      "data": {
        "id": "uuid1-uuid2",
        "source": "uuid1",
        "target": "uuid2"
      }
    }
  ]
}
```

---

### `GET /tree/subtree` — Arbre complet

**Paramètres** :
| Paramètre | Type | Défaut | Min | Max |
|---|---|---|---|---|
| `root_id` | UUID | **obligatoire** | - | - |
| `depth` | int | 2 | 1 | 5 |
| `include_spouses` | bool | true | - | - |

```
GET /tree/subtree?root_id=550e8400-...&depth=3&include_spouses=true
```

---

### `GET /tree/ancestors/{person_id}` — Arbre ascendant

Remonte les ancêtres (parents, grands-parents, arrière-grands-parents...).

```
GET /tree/ancestors/550e8400-...?generations=4
```
> `generations` : 1 à 8

---

### `GET /tree/descendants/{person_id}` — Arbre descendant

Descend les descendants (enfants, petits-enfants...).

```
GET /tree/descendants/550e8400-...?generations=3
```
> `generations` : 1 à 6

---

### `GET /tree/family/{person_id}` — Groupe familial immédiat

Retourne en une seule requête : **parents + conjoints + enfants** de la personne.

```
GET /tree/family/550e8400-...
```

---

### `GET /tree/path/{from_id}/{to_id}` — Chemin de parenté

Trouve le lien de parenté entre deux personnes (algorithme BFS).

```
GET /tree/path/550e8400-.../660e9500-...
```

---

### `GET /tree/neighbors` — Voisins proches

```
GET /tree/neighbors?person_id=550e8400-...&radius=1
```
> `radius=1` : relations directes  
> `radius=2` : relations des relations

---

### `GET /tree/pedigree/{person_id}` — Arbre en roue (Sosa)

Arbre pedigree avec **numérotation Sosa** et positions circulaires calculées.

```
GET /tree/pedigree/550e8400-...?generations=5
```

**Numérotation Sosa** :
- 1 = la personne de référence
- 2 = père, 3 = mère
- 4 = grand-père paternel, 5 = grand-mère paternelle, etc.

---

## 9. Module EVENTS

Les événements représentent les moments importants de la vie d'une personne.

**Types d'événements disponibles** :
| Type | Description |
|---|---|
| `birth` | Naissance |
| `death` | Décès |
| `marriage` | Mariage |
| `divorce` | Divorce |
| `baptism` | Baptême |
| `burial` | Enterrement |
| `education` | Formation / Diplôme |
| `employment` | Emploi / Carrière |
| `residence` | Lieu de résidence |
| `custom` | Événement personnalisé |

---

### `POST /events` — Créer un événement

**Accès** : EDITOR (avec droits ACL sur la personne), ADMIN

```json
{
  "person_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "birth",
  "date_start": "1867-11-07",
  "place": "Varsovie, Pologne",
  "description": "Naissance de Maria Sklodowska"
}
```

**Exemple avec période** (emploi, résidence) :
```json
{
  "person_id": "550e8400-...",
  "event_type": "employment",
  "date_start": "1891",
  "date_end": "1934",
  "place": "Paris, France",
  "description": "Professeure à la Sorbonne"
}
```

---

### `GET /events/person/{person_id}` — Événements d'une personne

```
GET /events/person/550e8400-...
GET /events/person/550e8400-...?event_type=marriage
```

---

### `GET /events/timeline/{person_id}` — Timeline chronologique

```
GET /events/timeline/550e8400-...
GET /events/timeline/550e8400-...?start_year=1860&end_year=1900
```

---

### `GET /events/{event_id}` — Détail d'un événement
### `PUT /events/{event_id}` — Modifier un événement

```json
{
  "place": "Varsovie, Royaume du Congrès",
  "description": "Description mise à jour"
}
```

### `DELETE /events/{event_id}` — Supprimer un événement

---

## 10. Module MEDIA

### `POST /media/upload` — Uploader un fichier

**Accès** : EDITOR (avec droits ACL), ADMIN  
**Format** : `multipart/form-data`

**Champs** :
| Champ | Type | Obligatoire | Description |
|---|---|:---:|---|
| `file` | fichier | ✅ | Le fichier à uploader |
| `owner_type` | string | ✅ | `person`, `event`, ou `user` |
| `owner_id` | UUID | ✅ | ID du propriétaire |
| `media_type` | string | ❌ | `image`, `document`, `pdf` (défaut: `image`) |
| `privacy_level` | string | ❌ | `public`, `family`, `private` (défaut: `private`) |

**Types de fichiers acceptés** : JPEG, PNG, WebP, PDF

**Réponse** :
```json
{
  "id": "770e8400-...",
  "filename": "photo_marie.jpg",
  "storage_key": "person/550e8400.../photo-abc123.jpg",
  "thumbnail_key": "thumbnails/person/550e8400.../photo-abc123.jpg",
  "url": "/api/v1/media/770e8400-...",
  "thumbnail_url": "/api/v1/media/770e8400-.../thumbnail"
}
```

> Une **miniature** est générée automatiquement pour les images.

---

### `GET /media/{media_id}` — Télécharger un fichier

Retourne le fichier en stream (image, PDF...).

---

### `GET /media/{media_id}/thumbnail` — Télécharger la miniature

---

### `GET /media/owner/{owner_type}/{owner_id}` — Médias d'une entité

```
GET /media/owner/person/550e8400-...
GET /media/owner/event/660e9500-...
```

---

### `PUT /media/{media_id}/privacy` — Changer la visibilité

```
PUT /media/770e8400-...}/privacy?privacy_level=public
```

---

### `DELETE /media/{media_id}` — Supprimer un média

Supprime le fichier physique ET la miniature du disque.

---

## 11. Module ADMIN

> ⚠️ **Tous ces endpoints nécessitent le rôle ADMIN.**

**Compte admin par défaut** :
```
Email    : admin@genealogie.com
Password : Admin123!
```

---

### Gestion des utilisateurs

#### `GET /admin/users` — Lister les utilisateurs
```
GET /admin/users?search=jean&page=1&limit=20
```

#### `GET /admin/users/{user_id}` — Détail d'un utilisateur

#### `PUT /admin/users/{user_id}` — Modifier un utilisateur
```json
{ "first_name": "Jean", "email": "nouveau@example.com" }
```

#### `PUT /admin/users/{user_id}/role` — Changer le rôle
```json
{ "role": "editor" }
```
> Valeurs : `admin` | `editor` | `reader`

#### `POST /admin/users/{user_id}/activate` — Activer un compte
#### `POST /admin/users/{user_id}/deactivate` — Désactiver un compte
#### `DELETE /admin/users/{user_id}` — Supprimer définitivement

---

### Gestion des ACL

Les ACL permettent de donner des droits fins sur des personnes spécifiques.

#### `GET /admin/acls?person_id={uuid}` — Lister les ACL d'une personne

#### `POST /admin/acls` — Créer une ACL
```json
{
  "person_id": "550e8400-...",
  "principal_type": "user",
  "principal_id": "660e9500-...",
  "permission": "write"
}
```

**`principal_type`** :
- `user` : donne accès à un utilisateur précis (passer son UUID dans `principal_id`)
- `role` : donne accès à tous les utilisateurs d'un rôle (passer `editor` ou `reader` dans `principal_id`)

**`permission`** :
- `read` : lecture seule
- `write` : lecture + modification
- `delete` : tous les droits

#### `DELETE /admin/acls/{acl_id}` — Révoquer une ACL

---

### Statistiques

#### `GET /admin/stats` — Statistiques globales
```json
{
  "users": { "total": 5, "active": 4, "by_role": { "admin": 1, "editor": 2, "reader": 2 } },
  "persons": { "total": 120, "by_privacy": { "public": 80, "family": 30, "private": 10 } },
  "relationships": { "total": 95, "parent_child": 60, "couple": 35 },
  "events": { "total": 200, "by_type": { "birth": 80, "death": 40, "marriage": 35 } },
  "media": { "total": 50 }
}
```

#### `GET /admin/stats/users` — Stats détaillées des utilisateurs
Inscriptions par mois, utilisateurs avec 2FA, dernières connexions.

#### `GET /admin/stats/persons` — Stats détaillées des personnes
Répartition par genre, décennie de naissance, lieux les plus fréquents.

---

### Export des données

#### `POST /admin/export/all?format=json` — Export JSON complet
Exporte toutes les données (users, persons, relations, events, media).

#### `POST /admin/export/all?format=gedcom` — Export GEDCOM 5.5.1
Format standard généalogique, compatible avec Ancestry, MyHeritage, etc.

#### `POST /admin/export/users` — Export CSV des utilisateurs

---

## 12. Codes d'erreur

| Code | Signification | Cause fréquente |
|---|---|---|
| `400` | Bad Request | Données invalides, cycle détecté dans l'arbre |
| `401` | Unauthorized | Token manquant, expiré ou invalide |
| `403` | Forbidden | Rôle insuffisant ou ACL manquante |
| `404` | Not Found | Ressource introuvable |
| `409` | Conflict | Email déjà utilisé, relation déjà existante |
| `422` | Unprocessable Entity | Erreur de validation Pydantic (champ manquant, mauvais format) |
| `429` | Too Many Requests | Rate limiting dépassé |

**Format standard d'erreur** :
```json
{
  "detail": "Person with id '550e8400-...' not found"
}
```

---

## 13. Workflow complet — Exemple pas à pas

Voici comment créer un arbre généalogique simple (famille Curie).

### Étape 1 — Se connecter en admin

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "admin@genealogie.com",
  "password": "Admin123!"
}
```
→ Récupérez `access_token` et stockez-le.

---

### Étape 2 — Créer un compte éditeur

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "editeur@example.com",
  "password": "Editeur123!",
  "first_name": "Paul",
  "last_name": "Martin"
}
```

Puis promouvoir en EDITOR (avec le token admin) :
```http
PUT /api/v1/admin/users/{user_id}/role
Authorization: Bearer <admin_token>
Content-Type: application/json

{ "role": "editor" }
```

---

### Étape 3 — Créer les personnes

```http
POST /api/v1/persons
Authorization: Bearer <token>
Content-Type: application/json

{ "first_name": "Władysław", "last_name": "Skłodowski", "gender": "male",
  "birth_date": "1832", "death_date": "1902", "is_living": false,
  "privacy_level": "public" }
```

```http
POST /api/v1/persons
Authorization: Bearer <token>
Content-Type: application/json

{ "first_name": "Marie", "last_name": "Curie", "maiden_name": "Skłodowska",
  "gender": "female", "birth_date": "1867-11-07", "birth_place": "Varsovie",
  "death_date": "1934-07-04", "death_place": "Passy", "is_living": false,
  "privacy_level": "public" }
```

```http
POST /api/v1/persons
Authorization: Bearer <token>
Content-Type: application/json

{ "first_name": "Pierre", "last_name": "Curie", "gender": "male",
  "birth_date": "1859-05-15", "death_date": "1906-04-19", "is_living": false,
  "privacy_level": "public" }
```

---

### Étape 4 — Créer les relations

Père → Marie :
```http
POST /api/v1/relationships
Authorization: Bearer <token>
Content-Type: application/json

{
  "type": "parent_child",
  "person_id_1": "<id_wladyslaw>",
  "person_id_2": "<id_marie>",
  "child_type": "biological"
}
```

Mariage Marie ↔ Pierre :
```http
POST /api/v1/relationships
Authorization: Bearer <token>
Content-Type: application/json

{
  "type": "couple",
  "person_id_1": "<id_marie>",
  "person_id_2": "<id_pierre>",
  "marriage_date": "1895-07-26",
  "marriage_place": "Sceaux, France"
}
```

---

### Étape 5 — Ajouter des événements

```http
POST /api/v1/events
Authorization: Bearer <token>
Content-Type: application/json

{
  "person_id": "<id_marie>",
  "event_type": "birth",
  "date_start": "1867-11-07",
  "place": "Varsovie, Pologne"
}
```

```http
POST /api/v1/events
Authorization: Bearer <token>
Content-Type: application/json

{
  "person_id": "<id_marie>",
  "event_type": "education",
  "date_start": "1891",
  "date_end": "1894",
  "place": "Paris, France",
  "description": "Études de physique et mathématiques à la Sorbonne"
}
```

---

### Étape 6 — Visualiser l'arbre

```http
GET /api/v1/tree/family/<id_marie>
Authorization: Bearer <token>
```

```http
GET /api/v1/tree/ancestors/<id_marie>?generations=3
Authorization: Bearer <token>
```

---

### Étape 7 — Exporter les données

```http
POST /api/v1/admin/export/all?format=gedcom
Authorization: Bearer <admin_token>
```

---

*Documentation générée pour Genealogie App v1.0.0*
