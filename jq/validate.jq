def sha(length):
  . as $input
  | test("^[0-9a-fA-F]{\(length)}$")
        or error("tag is not \(length)-char sha")
  | $input
;

def semver:
  . as $input
  | test("^v?[0-9]+\\.[0-9]+\\.[0-9]+(-[0-9A-Za-z.-]+)?(\\+[0-9A-Za-z.-]+)?$")
        or error("tag is not semver")
  | $input
;

def sha_or_semver(length):
  . as $input
  | try sha(length)
    catch ($input | semver)
;

def version:
  . as $input
  | test("^[0-9]+\\.[0-9]+\\.[0-9]+(-[0-9A-Za-z-]+(\\.[0-9A-Za-z-]+)*)?\\+?[0-9A-Za-z-]*$")
        or error("Version string does not meet expectations")
  | $input
;

def image_prefix($prefixes):
  . as $image
  | ($prefixes | map(select(length > 0))) as $allowed
  | (any($allowed[]; . as $prefix | $image | startswith($prefix))
     or error("Image is not in an allowed repository: \($image) (allowed prefixes: \($allowed | join(", ")))"))
  | $image
;
