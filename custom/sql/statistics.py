"""
COMMON_SQL dict of SQL snippets. This is the icare4u custom version in project,
where settings.STATS_CUSTOM_SQL = 'icare4u_front.custom.sql.statistics'
"""

CUSTOM_SQL = {

    ##################################
    # USERS_BY_TYPE, for tabulatedData
    ##################################

    'USERS_BY_TYPE': """
SELECT 'Spaarders' AS 'Type gebruiker'
      , SUM((CASE WHEN pind.profile_id IS NOT NULL THEN 1 ELSE 0 END)) AS 'Totaal nummer'
      , SUM((CASE WHEN pind.profile_id IS NOT NULL AND puser_user.is_active=1 THEN 1 ELSE 0 END)) AS 'Actief gebruikers'

FROM profile_userprofile AS puser
        LEFT JOIN cyclos_cc3profile AS cc3p
                ON cc3p.`id`=puser.`cc3profile_ptr_id`
        LEFT JOIN auth_user AS puser_user
                ON puser_user.`id`=cc3p.`user_id`
        LEFT JOIN profile_individualprofile AS pind
                ON pind.`profile_id`=puser.`cc3profile_ptr_id`
        LEFT JOIN cyclos_cc3community AS community
                ON cc3p.`community_id`=community.`id`
WHERE {{community_filter}} True

UNION ALL

SELECT
        'Winkeliers' AS 'Type gebruiker'
      , SUM((CASE WHEN pbus.profile_id IS NOT NULL THEN 1 ELSE 0 END)) AS 'Totaal nummer'
      , SUM((CASE WHEN pbus.profile_id IS NOT NULL AND puser_user.is_active=1 THEN 1 ELSE 0 END)) AS 'Actief gebruikers'

FROM profile_userprofile AS puser
        LEFT JOIN cyclos_cc3profile AS cc3p
                ON cc3p.`id`=puser.`cc3profile_ptr_id`
        LEFT JOIN auth_user AS puser_user
                ON puser_user.`id`=cc3p.`user_id`
        LEFT JOIN profile_businessprofile AS pbus
                ON pbus.`profile_id`=puser.`cc3profile_ptr_id`
        LEFT JOIN cyclos_cc3community AS community
                ON cc3p.`community_id`=community.`id`
WHERE {{community_filter}} True

UNION ALL

SELECT
        'Spaardoelen' AS 'Type gebruiker'
      , SUM((CASE WHEN pcha.profile_id IS NOT NULL THEN 1 ELSE 0 END)) AS 'Totaal nummer'
      , SUM((CASE WHEN pcha.profile_id IS NOT NULL AND puser_user.is_active=1 THEN 1 ELSE 0 END)) AS 'Actief gebruikers'

FROM profile_userprofile AS puser
        LEFT JOIN cyclos_cc3profile AS cc3p
                ON cc3p.`id`=puser.`cc3profile_ptr_id`
        LEFT JOIN auth_user AS puser_user
                ON puser_user.`id`=cc3p.`user_id`
        LEFT JOIN profile_charityprofile AS pcha
                ON pcha.`profile_id`=puser.`cc3profile_ptr_id`
        LEFT JOIN cyclos_cc3community AS community
                ON cc3p.`community_id`=community.`id`
WHERE {{community_filter}} True

UNION ALL

SELECT
        'Instellingen' AS 'Type gebruiker'
      , SUM((CASE WHEN pins.profile_id IS NOT NULL THEN 1 ELSE 0 END)) AS 'Totaal nummer'
      , SUM((CASE WHEN pins.profile_id IS NOT NULL AND puser_user.is_active=1 THEN 1 ELSE 0 END)) AS 'Actief gebruikers'

FROM profile_userprofile AS puser
        LEFT JOIN cyclos_cc3profile AS cc3p
                ON cc3p.`id`=puser.`cc3profile_ptr_id`
        LEFT JOIN auth_user AS puser_user
                ON puser_user.`id`=cc3p.`user_id`
        LEFT JOIN profile_institutionprofile AS pins
                ON pins.`profile_id`=puser.`cc3profile_ptr_id`
        LEFT JOIN cyclos_cc3community AS community
                ON cc3p.`community_id`=community.`id`
WHERE {{community_filter}} True
""",
    #######################################################
    # TOTAL_INDIVIDUAL_USERS_BY_MONTH, for discreteBarChart
    #######################################################
    # NB this doesn't do the differences (shown in wireframe) -- need to be handled in model

    # NEED to use DATE(CONCAT(YEAR( date_joined), '-', MONTH(date_joined), '-01')) AS 'x' for date - and then format in python (through 'extra')
    # this is to take advantage of Python internationalisation

    'TOTAL_INDIVIDUAL_USERS_BY_MONTH': """
SELECT a.mth as 'x', SUM(b.mtotal) as 'y1' FROM (SELECT EXTRACT(YEAR_MONTH FROM date_joined) AS 'mth'
FROM auth_user AS puser_user
	LEFT JOIN cyclos_cc3profile AS cc3p
		ON cc3p.`user_id`=puser_user.`id`
	LEFT JOIN profile_userprofile AS puser
		ON puser.`cc3profile_ptr_id`=cc3p.`id`
	LEFT JOIN profile_individualprofile AS pind
		ON pind.`profile_id`=puser.`cc3profile_ptr_id`
        LEFT JOIN cyclos_cc3community AS community
                ON cc3p.`community_id`=community.`id`
WHERE {{community_filter}} pind.`id` IS NOT NULL AND puser_user.`is_active`=1
GROUP BY EXTRACT(YEAR_MONTH FROM date_joined)) a, (SELECT EXTRACT(YEAR_MONTH FROM date_joined) AS 'mth', COUNT(*) AS 'mtotal'
FROM auth_user AS puser_user
	LEFT JOIN cyclos_cc3profile AS cc3p
		ON cc3p.`user_id`=puser_user.`id`
	LEFT JOIN profile_userprofile AS puser
		ON puser.`cc3profile_ptr_id`=cc3p.`id`
	LEFT JOIN profile_individualprofile AS pind
		ON pind.`profile_id`=puser.`cc3profile_ptr_id`
        LEFT JOIN cyclos_cc3community AS community
                ON cc3p.`community_id`=community.`id`
WHERE {{community_filter}} pind.`id` IS NOT NULL AND puser_user.`is_active`=1
GROUP BY EXTRACT(YEAR_MONTH FROM date_joined)) b
WHERE b.mth <= a.mth
GROUP BY a.mth
""",


###############################################
# TOTAL_OTHER_USERS_BY_MONTH, for multiBarChart
###############################################

'TOTAL_OTHER_USERS_BY_MONTH': """
SELECT q1.`x`, q2.`name`, count(q2.`id`) as 'y1', NULL as 'y2', NULL as 'y3'

FROM
    (SELECT EXTRACT(YEAR_MONTH FROM date_joined) AS 'x'

    FROM auth_user AS puser_user
    WHERE  puser_user.`is_active`=1
    GROUP BY EXTRACT(YEAR_MONTH FROM date_joined)
    ) q1,

    (SELECT puser_user.id, EXTRACT(YEAR_MONTH FROM date_joined) AS 'dj', 'Winkeliers' AS 'name'

    FROM auth_user AS puser_user
            LEFT JOIN cyclos_cc3profile AS cc3p
                    ON cc3p.`user_id`=puser_user.`id`
            LEFT JOIN profile_userprofile AS puser
                    ON puser.`cc3profile_ptr_id`=cc3p.`id`
            LEFT JOIN profile_businessprofile AS pind
                    ON pind.`profile_id`=puser.`cc3profile_ptr_id`
            LEFT JOIN cyclos_cc3community AS community
                    ON cc3p.`community_id`=community.`id`
    WHERE  pind.`id` IS NOT NULL AND puser_user.`is_active`=1
    ) q2

WHERE q2.`dj` <= q1.`x`

GROUP BY q1.`x`


UNION ALL


SELECT q1.`x`, q2.`name`, NULL as 'y1', count(q2.`id`) as 'y2', NULL as 'y3'

FROM
    (SELECT EXTRACT(YEAR_MONTH FROM date_joined) AS 'x'

    FROM auth_user AS puser_user
    WHERE  puser_user.`is_active`=1
    GROUP BY EXTRACT(YEAR_MONTH FROM date_joined)
    ) q1,

    (SELECT puser_user.id, EXTRACT(YEAR_MONTH FROM date_joined) AS 'dj', 'Instellingen' AS 'name'

    FROM auth_user AS puser_user
            LEFT JOIN cyclos_cc3profile AS cc3p
                    ON cc3p.`user_id`=puser_user.`id`
            LEFT JOIN profile_userprofile AS puser
                    ON puser.`cc3profile_ptr_id`=cc3p.`id`
            LEFT JOIN profile_institutionprofile AS pind
                    ON pind.`profile_id`=puser.`cc3profile_ptr_id`
            LEFT JOIN cyclos_cc3community AS community
                    ON cc3p.`community_id`=community.`id`
    WHERE  pind.`id` IS NOT NULL AND puser_user.`is_active`=1
    ) q2

WHERE q2.`dj` <= q1.`x`

GROUP BY q1.`x`


UNION ALL


SELECT q1.`x`, q2.`name`, NULL as 'y1', NULL as 'y2', count(q2.`id`) as 'y3'

FROM
    (SELECT EXTRACT(YEAR_MONTH FROM date_joined) AS 'x'

    FROM auth_user AS puser_user
    WHERE  puser_user.`is_active`=1
    GROUP BY EXTRACT(YEAR_MONTH FROM date_joined)
    ) q1,

    (SELECT puser_user.id, EXTRACT(YEAR_MONTH FROM date_joined) AS 'dj', 'Spaardoelen' AS 'name'

    FROM auth_user AS puser_user
            LEFT JOIN cyclos_cc3profile AS cc3p
                    ON cc3p.`user_id`=puser_user.`id`
            LEFT JOIN profile_userprofile AS puser
                    ON puser.`cc3profile_ptr_id`=cc3p.`id`
            LEFT JOIN profile_charityprofile AS pind
                    ON pind.`profile_id`=puser.`cc3profile_ptr_id`
            LEFT JOIN cyclos_cc3community AS community
                    ON cc3p.`community_id`=community.`id`
    WHERE  pind.`id` IS NOT NULL AND puser_user.`is_active`=1
    ) q2

WHERE q2.`dj` <= q1.`x`

GROUP BY q1.`x`
""",

}
