from flask import Blueprint, jsonify, request
from app.db import query, executeReturning
from app.normalize import normalizeAddress
from app.validation import ValidationError, sanitizeAuthor, sanitizeComment, validateSince

bp = Blueprint("api", __name__)


@bp.route("/property/<path:address>/")
def getProperty(address: str):
    norm = normalizeAddress(address)

    violations = query(
        """
        SELECT violation_date, violation_code, violation_status,
               violation_description, inspector_comments
        FROM violations
        WHERE address_normalized = %s
        ORDER BY violation_date DESC
        """,
        (norm,),
    )

    isScofflawRows = query(
        "SELECT 1 FROM scofflaws WHERE address_normalized = %s LIMIT 1",
        (norm,),
    )

    if not violations and not isScofflawRows:
        return jsonify({"error": "Address not found"}), 404

    lastDate = violations[0]["violation_date"].isoformat() if violations else None

    return jsonify(
        {
            "address": address.strip(),
            "last_violation_date": lastDate,
            "total_violation_count": len(violations),
            "violations": [
                {
                    "date": v["violation_date"].isoformat(),
                    "code": v["violation_code"],
                    "status": v["violation_status"],
                    "description": v["violation_description"],
                    "inspector_comments": v["inspector_comments"],
                }
                for v in violations
            ],
            "SCOFFLAW": bool(isScofflawRows),
        }
    )


@bp.route("/property/<path:address>/comments/", methods=["POST"])
def postComment(address: str):
    body = request.get_json(silent=True)
    if body is None:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    try:
        author = sanitizeAuthor(body.get("author"))
        comment = sanitizeComment(body.get("comment"))
    except ValidationError as e:
        return jsonify({"error": e.message}), 400

    norm = normalizeAddress(address)

    row = executeReturning(
        """
        INSERT INTO comments (address_normalized, author, comment_text)
        VALUES (%s, %s, %s)
        RETURNING id, created_at
        """,
        (norm, author, comment),
    )

    return jsonify(
        {
            "message": "Comment created",
            "id": row["id"],
            "address": address.strip(),
            "author": author,
            "created_at": row["created_at"].isoformat(),
        }
    ), 201
