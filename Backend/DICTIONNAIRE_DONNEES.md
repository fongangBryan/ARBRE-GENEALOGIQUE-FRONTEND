# Dictionnaire de Données — Genealogie App

**Projet** : Application de gestion d'arbre généalogique  
**Version** : 1.0.0  
**Niveau** : Conceptuel  
**Date** : Avril 2026

---

## Table des matières

1. [Entité UTILISATEUR](#1-entité-utilisateur)
2. [Entité PERSONNE](#2-entité-personne)
3. [Entité RELATION](#3-entité-relation)
4. [Entité ÉVÉNEMENT](#4-entité-événement)
5. [Entité MÉDIA](#5-entité-média)
6. [Entité CONTRÔLE_ACCÈS](#6-entité-contrôle_accès)
7. [Entité TAG](#7-entité-tag)
8. [Entité ASSOCIATION_PERSONNE_TAG](#8-entité-association_personne_tag)
9. [Entité HISTORIQUE_TAG](#9-entité-historique_tag)
10. [Synthèse des règles de gestion](#10-synthèse-des-règles-de-gestion)

---

## 1. Entité UTILISATEUR

**Nom de la table** : `users`  
**Description** : Représente un compte utilisateur de l'application. Chaque utilisateur possède un rôle qui détermine ses droits d'accès sur les données généalogiques.

| Attribut | Type | Longueur | Obligatoire | Valeurs / Contraintes | Description |
|---|---|:---:|:---:|---|---|
| adresse_email | Chaîne | 255 | ✅ | Format email valide, unique | Identifiant de connexion de l'utilisateur |
| mot_de_passe_hashé | Chaîne | 255 | ✅ | Haché avec bcrypt | Mot de passe chiffré, jamais stocké en clair |
| prénom | Chaîne | 100 | ❌ | — | Prénom de l'utilisateur |
| nom | Chaîne | 100 | ❌ | — | Nom de famille de l'utilisateur |
| rôle | Énumération | — | ✅ | `admin` \| `editor` \| `reader` | Niveau de permission dans l'application |
| est_actif | Booléen | — | ✅ | `true` par défaut | Indique si le compte est activé |
| est_vérifié | Booléen | — | ✅ | `false` par défaut | Indique si l'email a été vérifié |
| 2fa_activée | Booléen | — | ✅ | `false` par défaut | Indique si l'authentification à deux facteurs est activée |
| secret_totp | Chaîne | 100 | ❌ | Chiffré | Secret TOTP pour la génération des codes 2FA |
| secret_totp_temporaire | Chaîne | 100 | ❌ | Valide le temps de la configuration | Secret TOTP en cours de vérification lors de l'activation 2FA |
| date_création | Horodatage | — | ✅ | Généré automatiquement | Date et heure de création du compte |
| date_modification | Horodatage | — | ✅ | Mis à jour automatiquement | Date et heure de la dernière modification du profil |
| dernière_connexion | Horodatage | — | ❌ | Mis à jour à chaque connexion | Date et heure de la dernière connexion réussie |

**Règles de gestion :**
- Un utilisateur nouvellement inscrit obtient le rôle `reader` par défaut.
- Le mot de passe doit contenir au minimum 8 caractères.
- Un compte désactivé (`est_actif = false`) ne peut plus se connecter.
- Un seul compte admin est créé automatiquement lors de l'initialisation de l'application.

---

## 2. Entité PERSONNE

**Nom de la table** : `persons`  
**Description** : Représente un individu dans l'arbre généalogique. Une personne peut être vivante ou décédée, et son niveau de confidentialité contrôle qui peut consulter ses informations.

| Attribut | Type | Longueur | Obligatoire | Valeurs / Contraintes | Description |
|---|---|:---:|:---:|---|---|
| prénom | Chaîne | 100 | ✅ | — | Prénom de la personne |
| nom | Chaîne | 100 | ✅ | — | Nom de famille de la personne |
| nom_de_naissance | Chaîne | 100 | ❌ | — | Nom de jeune fille (pour les femmes mariées) |
| genre | Énumération | — | ❌ | `male` \| `female` \| `other` | Genre de la personne |
| date_naissance | Chaîne | 50 | ❌ | Format : `AAAA`, `AAAA-MM` ou `AAAA-MM-JJ` | Date de naissance (accepte les dates partielles) |
| lieu_naissance | Chaîne | 255 | ❌ | — | Ville, région ou pays de naissance |
| date_décès | Chaîne | 50 | ❌ | Format : `AAAA`, `AAAA-MM` ou `AAAA-MM-JJ` | Date de décès (accepte les dates partielles) |
| lieu_décès | Chaîne | 255 | ❌ | — | Ville, région ou pays du décès |
| est_vivant | Booléen | — | ✅ | `true` par défaut | Indique si la personne est encore en vie |
| biographie | Texte | illimité | ❌ | — | Biographie libre rédigée par l'utilisateur |
| profession | Chaîne | 255 | ❌ | — | Métier ou profession exercée |
| nationalité | Chaîne | 100 | ❌ | — | Nationalité de la personne |
| niveau_confidentialité | Énumération | — | ✅ | `public` \| `family` \| `private` | Contrôle la visibilité de la fiche |
| clé_photo_principale | Chaîne | 500 | ❌ | Clé de stockage interne | Référence à la photo de profil dans le système de stockage |
| créé_par | UUID | — | ❌ | Référence à un utilisateur | Utilisateur ayant créé la fiche de la personne |
| date_création | Horodatage | — | ✅ | Généré automatiquement | Date et heure de création de la fiche |
| date_modification | Horodatage | — | ✅ | Mis à jour automatiquement | Date et heure de la dernière modification |

**Règles de gestion :**
- Les champs `date_naissance` et `date_décès` acceptent des dates partielles (année seule, année et mois, ou date complète).
- Si `est_vivant = false`, la `date_décès` peut être renseignée.
- Le niveau `private` restreint la visibilité au créateur et aux utilisateurs disposant d'un droit ACL explicite.
- Le niveau `family` est accessible aux utilisateurs avec le rôle `editor` ou `admin`.

---

## 3. Entité RELATION

**Nom de la table** : `relationships`  
**Description** : Représente un lien familial entre deux personnes. Deux types de relations sont modélisés : le lien parent-enfant et le lien conjugal. Ces relations constituent la structure de l'arbre généalogique.

| Attribut | Type | Longueur | Obligatoire | Valeurs / Contraintes | Description |
|---|---|:---:|:---:|---|---|
| type_relation | Énumération | — | ✅ | `parent_child` \| `couple` | Nature du lien entre les deux personnes |
| type_filiation | Énumération | — | ❌ | `biological` \| `adoptive` \| `step` \| `guardian` | Précise la nature du lien parent-enfant (uniquement si `type_relation = parent_child`) |
| date_mariage | Chaîne | 50 | ❌ | Format date partielle | Date de mariage ou d'union (uniquement si `type_relation = couple`) |
| lieu_mariage | Chaîne | 255 | ❌ | — | Lieu de la cérémonie ou de l'union |
| date_divorce | Chaîne | 50 | ❌ | Format date partielle | Date de séparation ou de divorce |
| métadonnées | JSON | — | ❌ | Objet JSON libre | Informations complémentaires extensibles |
| date_création | Horodatage | — | ✅ | Généré automatiquement | Date et heure de création de la relation |
| date_modification | Horodatage | — | ✅ | Mis à jour automatiquement | Date et heure de la dernière modification |

**Règles de gestion :**
- Pour `type_relation = parent_child` : la première personne est le **parent**, la seconde est l'**enfant**.
- Pour `type_relation = couple` : l'ordre des deux personnes est indifférent.
- Le système interdit la création d'une relation qui provoquerait un **cycle** dans l'arbre (ex : une personne ne peut pas être son propre ancêtre).
- Une même paire de personnes ne peut pas avoir deux relations identiques simultanément.

**Valeurs de `type_filiation` :**

| Valeur | Signification |
|---|---|
| `biological` | Enfant biologique |
| `adoptive` | Enfant adopté |
| `step` | Beau-fils / belle-fille |
| `guardian` | Enfant sous tutelle |

---

## 4. Entité ÉVÉNEMENT

**Nom de la table** : `events`  
**Description** : Représente un fait ou un moment marquant de la vie d'une personne (naissance, mariage, emploi, résidence, etc.). Les événements constituent la timeline biographique d'un individu.

| Attribut | Type | Longueur | Obligatoire | Valeurs / Contraintes | Description |
|---|---|:---:|:---:|---|---|
| type_événement | Énumération | — | ✅ | Voir tableau ci-dessous | Catégorie de l'événement |
| date_début | Chaîne | 50 | ❌ | Format date partielle | Date de début de l'événement |
| date_fin | Chaîne | 50 | ❌ | Format date partielle | Date de fin (pour les événements sur une période) |
| lieu | Chaîne | 255 | ❌ | — | Lieu où s'est déroulé l'événement |
| description | Texte | illimité | ❌ | — | Description libre de l'événement |
| métadonnées | JSON | — | ❌ | Objet JSON libre | Informations complémentaires extensibles |
| date_création | Horodatage | — | ✅ | Généré automatiquement | Date et heure de saisie de l'événement |
| date_modification | Horodatage | — | ✅ | Mis à jour automatiquement | Date et heure de la dernière modification |

**Types d'événements disponibles :**

| Valeur | Libellé | Date fin possible |
|---|---|:---:|
| `birth` | Naissance | ❌ |
| `death` | Décès | ❌ |
| `marriage` | Mariage | ❌ |
| `divorce` | Divorce | ❌ |
| `baptism` | Baptême | ❌ |
| `burial` | Enterrement | ❌ |
| `education` | Formation / Diplôme | ✅ |
| `employment` | Emploi / Carrière | ✅ |
| `residence` | Lieu de résidence | ✅ |
| `custom` | Événement personnalisé | ✅ |

**Règles de gestion :**
- Chaque événement est lié à **une seule personne**.
- La `date_fin` ne peut être antérieure à la `date_début`.
- Les événements sont triés chronologiquement pour former la timeline de la personne.

---

## 5. Entité MÉDIA

**Nom de la table** : `media`  
**Description** : Représente un fichier numérique (photo, document, PDF) associé à une personne, un événement ou un utilisateur. Le fichier physique est stocké sur le système de fichiers ou un service de stockage objet.

| Attribut | Type | Longueur | Obligatoire | Valeurs / Contraintes | Description |
|---|---|:---:|:---:|---|---|
| type_propriétaire | Chaîne | 50 | ✅ | `person` \| `event` \| `user` | Type de l'entité à laquelle ce média est rattaché |
| type_média | Énumération | — | ✅ | `image` \| `document` \| `pdf` | Catégorie du fichier |
| niveau_confidentialité | Énumération | — | ✅ | `public` \| `family` \| `private` | Contrôle la visibilité du fichier |
| nom_fichier_original | Chaîne | 255 | ✅ | — | Nom du fichier tel qu'envoyé par l'utilisateur |
| clé_stockage | Chaîne | 500 | ✅ | Unique | Chemin ou clé d'accès au fichier dans le stockage |
| clé_miniature | Chaîne | 500 | ❌ | — | Chemin ou clé d'accès à la miniature générée (images uniquement) |
| type_mime | Chaîne | 100 | ✅ | Ex : `image/jpeg`, `application/pdf` | Type MIME du fichier |
| taille_fichier | Entier | — | ✅ | En octets | Taille du fichier en octets |
| date_création | Horodatage | — | ✅ | Généré automatiquement | Date et heure de l'envoi du fichier |

**Règles de gestion :**
- Les formats acceptés sont : JPEG, PNG, WebP et PDF.
- Une **miniature** est générée automatiquement pour les fichiers de type image.
- La `clé_stockage` est unique dans tout le système.
- La suppression d'un média entraîne la suppression du fichier physique et de sa miniature.

---

## 6. Entité CONTRÔLE_ACCÈS

**Nom de la table** : `access_controls`  
**Description** : Définit des droits d'accès granulaires sur une fiche personne pour un utilisateur ou un rôle spécifique. Permet de partager l'accès à une fiche privée sans modifier son niveau de confidentialité global.

| Attribut | Type | Longueur | Obligatoire | Valeurs / Contraintes | Description |
|---|---|:---:|:---:|---|---|
| type_principal | Énumération | — | ✅ | `user` \| `role` | Indique si le droit est accordé à un utilisateur précis ou à un rôle entier |
| identifiant_principal | Chaîne | 255 | ✅ | UUID utilisateur ou nom du rôle | Désigne le bénéficiaire du droit d'accès |
| permission | Énumération | — | ✅ | `read` \| `write` \| `delete` | Niveau de permission accordé |
| date_création | Horodatage | — | ✅ | Généré automatiquement | Date et heure d'attribution du droit |

**Niveaux de permission :**

| Valeur | Droits accordés |
|---|---|
| `read` | Consultation de la fiche uniquement |
| `write` | Consultation et modification de la fiche |
| `delete` | Tous les droits, y compris la suppression |

**Règles de gestion :**
- Un ACL de type `role` s'applique à **tous** les utilisateurs portant ce rôle.
- Un ACL de type `user` s'applique à **un seul** utilisateur identifié.
- La permission `write` implique automatiquement `read`.
- La permission `delete` implique automatiquement `read` et `write`.
- Seul un administrateur peut créer, modifier ou supprimer des ACL.

---

## 7. Entité TAG

**Nom de la table** : `tags`  
**Description** : Étiquette libre permettant de catégoriser et de regrouper des personnes dans l'arbre généalogique. Les tags facilitent la navigation et le filtrage par thématique (branche familiale, statut, groupe génétique, etc.).

| Attribut | Type | Longueur | Obligatoire | Valeurs / Contraintes | Description |
|---|---|:---:|:---:|---|---|
| libellé | Chaîne | 100 | ✅ | Unique | Nom du tag, doit être unique dans l'application |
| description | Chaîne | 500 | ❌ | — | Explication de la signification ou de l'usage du tag |
| couleur | Chaîne | 7 | ✅ | Format hexadécimal `#RRGGBB`, défaut `#02E08E` | Couleur d'affichage du tag dans l'interface |
| icône | Chaîne | 50 | ❌ | Nom d'icône (ex : `star`, `heart`) | Icône associée pour l'affichage visuel |
| créé_par | UUID | — | ❌ | Référence à un utilisateur | Utilisateur ayant créé le tag |
| date_création | Horodatage | — | ✅ | Généré automatiquement | Date et heure de création du tag |

**Exemples de tags :**

| Libellé | Usage |
|---|---|
| Ancêtre direct | Marquer les ancêtres en ligne directe |
| Branche maternelle | Regrouper la famille de la mère |
| DNA match | Correspondance ADN confirmée |
| Vétéran | Personne ayant servi dans l'armée |
| Immigré | Personne ayant émigré dans un autre pays |

---

## 8. Entité ASSOCIATION_PERSONNE_TAG

**Nom de la table** : `person_tags`  
**Description** : Table d'association représentant la relation plusieurs-à-plusieurs entre les personnes et les tags. Une personne peut avoir plusieurs tags, et un tag peut être appliqué à plusieurs personnes.

| Attribut | Type | Longueur | Obligatoire | Valeurs / Contraintes | Description |
|---|---|:---:|:---:|---|---|
| date_association | Horodatage | — | ✅ | Généré automatiquement | Date et heure à laquelle le tag a été attribué à la personne |

**Cardinalités :**
- Une **PERSONNE** peut avoir `0` à `N` tags
- Un **TAG** peut être attribué à `0` à `N` personnes

---

## 9. Entité HISTORIQUE_TAG

**Nom de la table** : `person_tag_history`  
**Description** : Journal d'audit traçant chaque attribution ou retrait de tag sur une personne. Permet de conserver un historique complet des changements de catégorisation.

| Attribut | Type | Longueur | Obligatoire | Valeurs / Contraintes | Description |
|---|---|:---:|:---:|---|---|
| action | Chaîne | 20 | ✅ | `added` \| `removed` | Nature de l'opération effectuée |
| effectué_par | UUID | — | ❌ | Référence à un utilisateur | Utilisateur ayant réalisé l'opération |
| date_opération | Horodatage | — | ✅ | Généré automatiquement | Date et heure exacte de l'opération |

**Règles de gestion :**
- Chaque modification de tag sur une personne génère une entrée dans cet historique.
- Cet historique est en **lecture seule** — aucune entrée ne peut être modifiée ou supprimée.

---

## 10. Synthèse des règles de gestion

### Gestion des droits d'accès

| Rôle | Lecture | Création | Modification | Suppression | Administration |
|---|:---:|:---:|:---:|:---:|:---:|
| READER | ✅ (public) | ❌ | ❌ | ❌ | ❌ |
| EDITOR | ✅ (public + family + ACL) | ✅ | ✅ (avec ACL) | ❌ | ❌ |
| ADMIN | ✅ (tout) | ✅ | ✅ | ✅ | ✅ |

### Niveaux de confidentialité des personnes

| Niveau | READER | EDITOR | ADMIN | Utilisateur avec ACL |
|---|:---:|:---:|:---:|:---:|
| `public` | ✅ | ✅ | ✅ | ✅ |
| `family` | ❌ | ✅ | ✅ | ✅ |
| `private` | ❌ | ❌ | ✅ | ✅ |

### Format des dates partielles

L'application accepte trois niveaux de précision pour les dates historiques :

| Format | Exemple | Précision |
|---|---|---|
| `AAAA` | `1867` | Année uniquement |
| `AAAA-MM` | `1867-11` | Année et mois |
| `AAAA-MM-JJ` | `1867-11-07` | Date complète |

### Contraintes d'intégrité de l'arbre

- Une personne **ne peut pas être son propre ancêtre** (détection de cycle).
- Une personne **ne peut pas avoir deux fois le même parent biologique** du même genre.
- La suppression d'une personne entraîne la suppression en cascade de ses relations, événements, médias et tags associés.

---

*Dictionnaire de données — Genealogie App v1.0.0 — Avril 2026*
