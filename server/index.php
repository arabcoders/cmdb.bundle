<?php

header('Content-Type: application/json');

$id = $_GET['id'] ?? null;
$query = $_GET['q'] ?? $_GET['query'] ?? null;

if (empty($query) && empty($id)) {
    http_response_code(400);
    exit(1);
}

function n(string $title): string
{
    return strtolower($title);
}

function clean_up_string(string $s): string
{
    # Ands.
    $s = str_replace('&', 'and', $s);

    # Pre-process the string a bit to remove punctuation.
    # !"#$%&'()*+,-./:;<=>?@[\]^_`{|}~
    $pre = preg_quote('!"#$%&\'()*+,-./:;<=>?@[\]^_`{|}~', '/');
    $s = preg_replace('/[' . $pre . ']/', ' ', $s);

    # Lowercase it.
    $s = strtolower($s);

    # Strip leading "the/a"
    $s = preg_replace('/^(the|a) /', '', $s);

    # Spaces.
    $s = preg_replace('/[ ]+/', ' ', $s);

    return trim($s);
}


if (!empty($query)) {
    $query = n(rawurldecode($query));
}

$data = json_decode(file_get_contents(__DIR__ . '/data.json'), true);
$matchedItems = [];

foreach ($data as $item) {
    if (null !== $id) {
        if ($item['id'] === $id) {
            $matchedItems[] = $item;
            break;
        }
        continue;
    }

    $matchers = $item['matcher'] ?? [];
    $matchers[] = $item['title'];
    $matchers[] = clean_up_string($item['title']);

    foreach ($matchers as $matcher) {
        if (false !== str_starts_with(n($matcher), $query)) {
            $matchedItems[] = $item;
            break;
        }
    }
}

if (empty($matchedItems)) {
    http_response_code(404);
    exit(1);
}

echo json_encode($matchedItems);
